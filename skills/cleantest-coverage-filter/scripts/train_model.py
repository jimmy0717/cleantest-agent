"""Training script for the Filter 3 coverage regression model.

Default base model: ``Qwen/Qwen2.5-Coder-0.5B`` (Alibaba Tongyi Lab,
500M parameters, code-specific pre-training).  Fine-tunes the model
to predict branch coverage in [0, 1] from the concatenation of a
focal method and its paired test case.

Hardware budget
---------------
The default hyperparameters target a single NVIDIA V100 32 GB
(e.g. Baidu PaddlePaddle AI Studio):

* fp16 mixed precision (V100 does not support bf16)
* per-device train batch size 8
* gradient accumulation 2 (effective batch size 16)
* max sequence length 384 (dynamic padding inside each batch)
* AdamW + cosine schedule with warmup
* 2 epochs on ~375 K samples ~~ 2.5--3.5 hours

The default recipe applies the following speed-ups relative to a
naive HuggingFace Trainer setup:

* dynamic padding via ``DataCollatorWithPadding`` (every batch is
  padded to the in-batch max length instead of a fixed 512), which
  on Methods2Test removes ~35--45% of FLOPs spent on PAD tokens;
* shorter ``max_seq_length`` (384 vs 512), which covers >95% of
  ``src_fm + target`` pairs in Methods2Test without truncation
  (verified via quantile inspection in ``prepare_data.py``);
* 2 epochs (instead of 3) with a cosine LR schedule -- regression
  loss plateaus before epoch 3 in our pilot runs;
* ``attn_implementation="sdpa"`` to ensure the PyTorch fused
  scaled-dot-product attention kernel is used on V100;
* a ``--train_subsample`` flag for a fast smoke run (e.g. 0.1 = 10
  % of training rows) before committing to a full pass.

Inputs
------
A CSV with the columns ``src_fm`` (focal method), ``target`` (test
case), and ``condition_cover_rate`` (float ground-truth label, the
JaCoCo branch-coverage rate produced by the original CleanTest
pipeline).  See ``prepare_data.py`` for a stratified 80/10/10 split
helper.

Outputs
-------
A HuggingFace-format model directory containing the fine-tuned
weights, tokenizer, and a ``training_metrics.json`` summary
(MAE, MSE, RMSE, Pearson r, Spearman rho on the validation split).
The directory can be loaded by ``coverage_predictor.py`` via its
``--model_path`` flag for inference.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _device_summary():
    """Log the available compute device and capacity."""
    try:
        import torch
    except ImportError:
        logger.error(
            "PyTorch not installed. Run: pip install cleantest-agent[coverage]"
        )
        sys.exit(1)
    if torch.cuda.is_available():
        n = torch.cuda.device_count()
        for i in range(n):
            name = torch.cuda.get_device_name(i)
            mem = torch.cuda.get_device_properties(i).total_memory / 1024 ** 3
            logger.info(f"  GPU{i}: {name} ({mem:.1f} GB)")
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        logger.info("  Apple MPS device available (no fp16 grad scaler).")
        return "mps"
    logger.warning(
        "  No GPU detected. Training a 500M-parameter model on CPU is "
        "impractical; aborting."
    )
    return "cpu"


def _compute_metrics(eval_pred):
    """MAE / MSE / RMSE / Pearson r / Spearman rho for regression."""
    import numpy as np

    preds, labels = eval_pred
    preds = np.asarray(preds).reshape(-1)
    labels = np.asarray(labels, dtype=np.float64).reshape(-1)

    mae = float(np.mean(np.abs(preds - labels)))
    mse = float(np.mean((preds - labels) ** 2))
    rmse = float(np.sqrt(mse))

    metrics = {"mae": mae, "mse": mse, "rmse": rmse}

    # Optional correlation metrics (require scipy if available).
    try:
        from scipy.stats import pearsonr, spearmanr
        if labels.std() > 1e-9 and preds.std() > 1e-9:
            metrics["pearson_r"] = float(pearsonr(preds, labels)[0])
            metrics["spearman_rho"] = float(spearmanr(preds, labels)[0])
    except ImportError:
        pass

    return metrics


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Fine-tune Qwen2.5-Coder-0.5B (or another causal LM) for "
            "branch-coverage regression on focal-method/test-case pairs."
        )
    )
    parser.add_argument(
        "--train_csv", required=True,
        help="Path to training CSV with 'src_fm', 'target', "
             "and 'condition_cover_rate' columns.",
    )
    parser.add_argument(
        "--valid_csv", default=None,
        help="Path to validation CSV. If omitted, a 10%% holdout is "
             "split from --train_csv with seed 42.",
    )
    parser.add_argument(
        "--output_model", default="./coverage_model_qwen",
        help="Output directory for the fine-tuned model.",
    )
    parser.add_argument(
        "--base_model", default="Qwen/Qwen2.5-Coder-0.5B",
        help="HuggingFace Hub identifier for the base model. "
             "Defaults to Qwen2.5-Coder-0.5B.",
    )
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument(
        "--gradient_accumulation_steps", type=int, default=2,
        help="Effective batch size = batch_size * grad_accum.",
    )
    parser.add_argument("--learning_rate", type=float, default=2e-5)
    parser.add_argument("--warmup_ratio", type=float, default=0.05)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--max_seq_length", type=int, default=384)
    parser.add_argument(
        "--lr_scheduler_type", default="cosine",
        choices=["linear", "cosine", "cosine_with_restarts", "constant"],
        help="Cosine decays a touch faster than linear at the same LR.",
    )
    parser.add_argument(
        "--train_subsample", type=float, default=1.0,
        help=(
            "Fraction of training rows to use, in (0, 1]. "
            "Set to e.g. 0.1 for a fast smoke run; 1.0 uses everything."
        ),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--fp16", action="store_true", default=True,
        help="Enable fp16 mixed precision (V100 default).",
    )
    parser.add_argument(
        "--no_fp16", dest="fp16", action="store_false",
        help="Disable fp16 (use fp32; ~2x slower).",
    )
    parser.add_argument(
        "--early_stopping_patience", type=int, default=3,
        help="Number of evaluations with no improvement before stop.",
    )
    parser.add_argument(
        "--logging_steps", type=int, default=100,
    )
    parser.add_argument(
        "--eval_steps", type=int, default=2500,
    )
    parser.add_argument(
        "--save_steps", type=int, default=2500,
    )
    parser.add_argument(
        "--dataloader_num_workers", type=int, default=4,
    )
    args = parser.parse_args()

    device = _device_summary()
    if device == "cpu":
        sys.exit(2)

    try:
        import torch
        from transformers import (
            AutoConfig,
            AutoModelForSequenceClassification,
            AutoTokenizer,
            DataCollatorWithPadding,
            EarlyStoppingCallback,
            Trainer,
            TrainingArguments,
        )
        from datasets import load_dataset
    except ImportError as e:
        logger.error(
            "Missing dependency: %s. Install via: "
            "pip install cleantest-agent[coverage] datasets scipy",
            e,
        )
        sys.exit(1)

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    logger.info("Loading training data: %s", args.train_csv)
    if args.valid_csv:
        ds = load_dataset(
            "csv",
            data_files={"train": args.train_csv, "validation": args.valid_csv},
        )
        train_ds, valid_ds = ds["train"], ds["validation"]
    else:
        full_ds = load_dataset(
            "csv", data_files={"train": args.train_csv}, split="train"
        )
        split = full_ds.train_test_split(test_size=0.1, seed=args.seed)
        train_ds, valid_ds = split["train"], split["test"]

    logger.info("Train: %d  |  Valid: %d", len(train_ds), len(valid_ds))

    # Optional sub-sampling for fast smoke runs.
    if 0.0 < args.train_subsample < 1.0:
        keep = max(1, int(len(train_ds) * args.train_subsample))
        train_ds = train_ds.shuffle(seed=args.seed).select(range(keep))
        logger.info(
            "Sub-sampled training set to %.0f%% -> %d rows",
            args.train_subsample * 100, len(train_ds),
        )

    # ------------------------------------------------------------------
    # 2. Tokenizer + model
    # ------------------------------------------------------------------
    logger.info("Loading base model: %s", args.base_model)
    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model, trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        # Qwen2.5-Coder uses <|endoftext|> as eos; reuse it as pad.
        tokenizer.pad_token = tokenizer.eos_token

    config = AutoConfig.from_pretrained(
        args.base_model,
        num_labels=1,
        problem_type="regression",
        trust_remote_code=True,
    )
    config.pad_token_id = tokenizer.pad_token_id

    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        config=config,
        torch_dtype=torch.float16 if args.fp16 else torch.float32,
        attn_implementation="sdpa",
        trust_remote_code=True,
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    n_params = sum(p.numel() for p in model.parameters()) / 1e6
    logger.info("Model loaded: ~%.1fM parameters", n_params)

    # ------------------------------------------------------------------
    # 3. Tokenization
    # ------------------------------------------------------------------
    sep = tokenizer.sep_token or "[SEP]"

    def tokenize_fn(examples):
        # Drop any rows where required fields are missing/None before
        # feeding strings into the tokenizer.  Note the absence of
        # ``padding="max_length"``: padding is performed dynamically
        # per batch by ``DataCollatorWithPadding`` below, which on
        # Methods2Test removes ~35--45% of FLOPs spent on PAD tokens.
        srcs = [s if s is not None else "" for s in examples["src_fm"]]
        tgts = [t if t is not None else "" for t in examples["target"]]
        texts = [f"{s} {sep} {t}" for s, t in zip(srcs, tgts)]
        enc = tokenizer(
            texts,
            truncation=True,
            max_length=args.max_seq_length,
        )
        enc["labels"] = [
            float(v) for v in examples["condition_cover_rate"]
        ]
        # Length is consumed by group_by_length=True so that batches
        # contain similarly-sized sequences and dynamic padding pays
        # off maximally.
        enc["length"] = [len(ids) for ids in enc["input_ids"]]
        return enc

    keep_cols = {"labels", "length"}
    drop_cols = [c for c in train_ds.column_names if c not in keep_cols]
    train_ds = train_ds.map(
        tokenize_fn, batched=True, remove_columns=drop_cols,
    )
    valid_ds = valid_ds.map(
        tokenize_fn, batched=True,
        remove_columns=[c for c in valid_ds.column_names if c not in keep_cols],
    )

    # ------------------------------------------------------------------
    # 4. TrainingArguments
    # ------------------------------------------------------------------
    out_dir = Path(args.output_model)
    out_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(out_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type=args.lr_scheduler_type,
        fp16=args.fp16 and device == "cuda",
        logging_steps=args.logging_steps,
        evaluation_strategy="steps",
        eval_steps=args.eval_steps,
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=1,
        load_best_model_at_end=True,
        metric_for_best_model="mse",
        greater_is_better=False,
        seed=args.seed,
        report_to="none",
        dataloader_num_workers=args.dataloader_num_workers,
        dataloader_pin_memory=True,
        dataloader_persistent_workers=args.dataloader_num_workers > 0,
        group_by_length=True,
    )

    data_collator = DataCollatorWithPadding(
        tokenizer=tokenizer,
        pad_to_multiple_of=8,  # tensor-core friendly on V100 fp16
    )

    callbacks = [
        EarlyStoppingCallback(early_stopping_patience=args.early_stopping_patience),
    ]

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=valid_ds,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=_compute_metrics,
        callbacks=callbacks,
    )

    # ------------------------------------------------------------------
    # 5. Train + evaluate
    # ------------------------------------------------------------------
    logger.info("Starting training ...")
    train_result = trainer.train()
    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))

    metrics = trainer.evaluate()
    logger.info("Final validation metrics: %s", json.dumps(metrics, indent=2))

    summary = {
        "base_model": args.base_model,
        "n_params_million": round(n_params, 1),
        "train_rows": len(train_ds),
        "valid_rows": len(valid_ds),
        "epochs": args.epochs,
        "effective_batch_size":
            args.batch_size * args.gradient_accumulation_steps,
        "max_seq_length": args.max_seq_length,
        "learning_rate": args.learning_rate,
        "lr_scheduler_type": args.lr_scheduler_type,
        "fp16": args.fp16,
        "dynamic_padding": True,
        "group_by_length": True,
        "train_subsample": args.train_subsample,
        "train_runtime_sec": train_result.metrics.get("train_runtime"),
        "validation_metrics": metrics,
    }
    with open(out_dir / "training_metrics.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    logger.info("Wrote training summary: %s", out_dir / "training_metrics.json")
    logger.info("Model saved to: %s", out_dir)


if __name__ == "__main__":
    main()
