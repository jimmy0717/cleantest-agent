"""Training script for GPT-2 coverage regression model.

This script fine-tunes a GPT-2 model to predict branch coverage
from focal method + test case code. It follows the same approach
as the original CleanTest reward_regression_gpt2.py but with
cleaner argument handling.

Requires: GPU with >= 8GB VRAM, PyTorch, Transformers.
Training time: ~6 hours on RTX 3090/4090.
"""

import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Train GPT-2 coverage regression model"
    )
    parser.add_argument(
        "--train_csv", required=True,
        help="Path to training CSV with 'src_fm', 'target', and "
             "'condition_cover_rate' columns"
    )
    parser.add_argument(
        "--valid_csv", default=None,
        help="Path to validation CSV (same format)"
    )
    parser.add_argument(
        "--output_model", default="./coverage_model",
        help="Output directory for trained model"
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=2e-5)
    parser.add_argument("--max_seq_length", type=int, default=512)
    parser.add_argument(
        "--base_model", default="openai-community/gpt2",
        help="Base model from HuggingFace Hub"
    )
    args = parser.parse_args()

    # Check GPU
    try:
        import torch
        if not torch.cuda.is_available():
            logger.warning(
                "No GPU detected. Training will be very slow. "
                "Consider using --skip_coverage in the pipeline instead."
            )
        else:
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        logger.error("PyTorch not installed. Run: pip install torch")
        sys.exit(1)

    # Check dependencies
    try:
        from transformers import (
            GPT2Config,
            GPT2ForSequenceClassification,
            GPT2Tokenizer,
            Trainer,
            TrainingArguments,
        )
        from datasets import load_dataset
    except ImportError:
        logger.error(
            "transformers/datasets not installed. "
            "Run: pip install transformers datasets"
        )
        sys.exit(1)

    # Load data
    logger.info(f"Loading training data: {args.train_csv}")
    dataset = load_dataset(
        "csv", data_files={"train": args.train_csv},
        split="train"
    )
    if args.valid_csv:
        valid_dataset = load_dataset(
            "csv", data_files={"validation": args.valid_csv},
            split="validation"
        )
    else:
        split = dataset.train_test_split(test_size=0.1, seed=42)
        dataset = split["train"]
        valid_dataset = split["test"]

    logger.info(f"Train: {len(dataset)}, Valid: {len(valid_dataset)}")

    # Tokenizer
    tokenizer = GPT2Tokenizer.from_pretrained(args.base_model)
    tokenizer.pad_token = tokenizer.eos_token

    def tokenize_fn(examples):
        texts = [
            f"{src} [SEP] {tgt}"
            for src, tgt in zip(examples["src_fm"], examples["target"])
        ]
        tokenized = tokenizer(
            texts,
            truncation=True,
            max_length=args.max_seq_length,
            padding="max_length",
        )
        tokenized["labels"] = [
            float(v) for v in examples["condition_cover_rate"]
        ]
        return tokenized

    dataset = dataset.map(tokenize_fn, batched=True, remove_columns=dataset.column_names)
    valid_dataset = valid_dataset.map(tokenize_fn, batched=True, remove_columns=valid_dataset.column_names)

    # Model
    config = GPT2Config.from_pretrained(args.base_model, num_labels=1)
    config.pad_token_id = tokenizer.pad_token_id
    model = GPT2ForSequenceClassification.from_pretrained(
        args.base_model, config=config
    )
    model.config.pad_token_id = tokenizer.pad_token_id

    # Training
    training_args = TrainingArguments(
        output_dir=args.output_model,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        learning_rate=args.learning_rate,
        logging_steps=100,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        eval_dataset=valid_dataset,
    )

    logger.info("Starting training...")
    trainer.train()
    trainer.save_model(args.output_model)
    tokenizer.save_pretrained(args.output_model)
    logger.info(f"Model saved to: {args.output_model}")


if __name__ == "__main__":
    main()
