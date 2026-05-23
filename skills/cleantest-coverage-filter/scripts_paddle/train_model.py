"""Filter 3 coverage regression training (PaddlePaddle version).

Designed for Baidu PaddlePaddle AI Studio's PaddlePaddle 2.x image
on a single NVIDIA V100 32 GB. Uses ``paddlenlp`` to fine-tune
``Qwen/Qwen2.5-Coder-0.5B`` as a single-scalar regressor.

Inputs
------
A CSV with columns ``src_fm``, ``target``, ``condition_cover_rate``.

Outputs
-------
A PaddleNLP-format model directory containing the fine-tuned
weights, tokenizer, and a ``training_metrics.json`` summary.
The directory can be loaded by ``coverage_predictor.py``.
"""

import argparse
import json
import logging
import math
import os
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _device_summary():
    try:
        import paddle
    except ImportError:
        logger.error("paddle not installed; this script requires PaddlePaddle.")
        sys.exit(1)
    if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
        gpu_id = 0
        name = paddle.device.cuda.get_device_name(gpu_id)
        props = paddle.device.cuda.get_device_properties(gpu_id)
        mem_gb = props.total_memory / 1024 ** 3
        logger.info("  GPU: %s (%.1f GB)", name, mem_gb)
        return "gpu"
    logger.warning("  No GPU detected; aborting.")
    return "cpu"


def _compute_regression_metrics(preds, labels):
    import numpy as np
    preds = np.asarray(preds, dtype=np.float64).reshape(-1)
    labels = np.asarray(labels, dtype=np.float64).reshape(-1)
    mae = float(np.mean(np.abs(preds - labels)))
    mse = float(np.mean((preds - labels) ** 2))
    rmse = float(math.sqrt(mse))
    metrics = {"mae": mae, "mse": mse, "rmse": rmse}
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
        description="Fine-tune Qwen2.5-Coder-0.5B for coverage regression (Paddle)."
    )
    parser.add_argument("--train_csv", required=True)
    parser.add_argument("--valid_csv", required=True)
    parser.add_argument("--output_model", default="./coverage_model_qwen_paddle")
    parser.add_argument("--base_model", default="Qwen/Qwen2.5-Coder-0.5B")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=2)
    parser.add_argument("--learning_rate", type=float, default=2e-5)
    parser.add_argument("--warmup_ratio", type=float, default=0.05)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--max_seq_length", type=int, default=384)
    parser.add_argument("--lr_scheduler_type", default="cosine",
                        choices=["linear", "cosine", "constant"])
    parser.add_argument("--train_subsample", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--logging_steps", type=int, default=100)
    parser.add_argument("--eval_steps", type=int, default=2500)
    parser.add_argument("--save_steps", type=int, default=2500)
    parser.add_argument("--dataloader_num_workers", type=int, default=4)
    parser.add_argument("--fp16", action="store_true", default=False,
                        help="Mixed precision fp16 (V100). Prefer --bf16 on A100/A800.")
    parser.add_argument("--bf16", action="store_true", default=False,
                        help="Mixed precision bf16 (A100/A800/H100; numerically stable).")
    parser.add_argument("--clip_labels", action="store_true", default=True,
                        help="Clip condition_cover_rate into [0, 1] before training.")
    args = parser.parse_args()

    if args.fp16 and args.bf16:
        logger.error("--fp16 and --bf16 are mutually exclusive.")
        sys.exit(2)

    device = _device_summary()
    if device == "cpu":
        sys.exit(2)

    try:
        import numpy as np
        import paddle
        import pandas as pd
        from paddlenlp.transformers import (
            AutoTokenizer,
            Qwen2ForSequenceClassification,
        )
        from paddlenlp.trainer import (
            Trainer,
            TrainingArguments,
            EarlyStoppingCallback,
        )
        from paddlenlp.data import DataCollatorWithPadding
        from paddle.io import Dataset
    except ImportError as e:
        logger.error(
            "Missing dependency: %s. Install: pip install -U paddlenlp scipy pandas",
            e,
        )
        sys.exit(1)

    paddle.seed(args.seed)
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

    # ------------------------------------------------------------------
    # 1. Load CSVs into a tiny in-memory Dataset
    # ------------------------------------------------------------------
    logger.info("Loading: %s", args.train_csv)
    df_tr = pd.read_csv(args.train_csv)
    df_va = pd.read_csv(args.valid_csv)
    needed = {"src_fm", "target", "condition_cover_rate"}
    if not needed.issubset(df_tr.columns):
        logger.error("train_csv missing columns: %s",
                     needed - set(df_tr.columns))
        sys.exit(2)

    df_tr = df_tr.dropna(subset=list(needed)).reset_index(drop=True)
    df_va = df_va.dropna(subset=list(needed)).reset_index(drop=True)
    logger.info("Train: %d  |  Valid: %d", len(df_tr), len(df_va))

    # Clip cover rate into [0, 1] -- a tiny fraction of LessIsMore-FSE2025
    # rows have rate > 1 (suspected upstream noise); clipping is harmless
    # and prevents the regression head from chasing impossible targets.
    if args.clip_labels:
        for d, name in [(df_tr, "train"), (df_va, "valid")]:
            n_clip = int(((d["condition_cover_rate"] < 0) |
                          (d["condition_cover_rate"] > 1)).sum())
            if n_clip > 0:
                d["condition_cover_rate"] = d["condition_cover_rate"].clip(0.0, 1.0)
                logger.info("Clipped %d %s rows into [0, 1].", n_clip, name)

    if 0.0 < args.train_subsample < 1.0:
        df_tr = df_tr.sample(
            frac=args.train_subsample, random_state=args.seed,
        ).reset_index(drop=True)
        logger.info("Sub-sampled training set to %.0f%% -> %d rows",
                    args.train_subsample * 100, len(df_tr))

    # ------------------------------------------------------------------
    # 2. Tokenizer + model
    # ------------------------------------------------------------------
    logger.info("Loading base model: %s", args.base_model)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    if args.bf16:
        dtype = "bfloat16"
    elif args.fp16:
        dtype = "float16"
    else:
        dtype = "float32"
    logger.info("Compute dtype: %s", dtype)

    model = Qwen2ForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=1,
        problem_type="regression",
        dtype=dtype,
        convert_from_torch=True,
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    n_params = sum(p.numel() for p in model.parameters()) / 1e6
    n_params = float(n_params) if hasattr(n_params, 'item') else n_params
    logger.info("Model loaded: ~%.1fM parameters", n_params)

    # --- Wrap forward with sigmoid + MSE so prediction stays in [0, 1] ---
    # The default Qwen2ForSequenceClassification regression head emits a raw
    # scalar logit that is unbounded; for branch coverage which lives in
    # [0, 1] this means early training spends many steps just pulling the
    # output from O(10) down to O(0.1).  Squashing with sigmoid gives the
    # head a calibrated output range from step 0 and stabilises fp16/bf16
    # mixed precision training.
    import paddle.nn.functional as F
    _orig_forward = model.forward

    def _bounded_forward(self, *fwd_args, **fwd_kwargs):
        labels = fwd_kwargs.pop("labels", None)
        out = _orig_forward(*fwd_args, **fwd_kwargs)
        logits = out.logits if hasattr(out, "logits") else out[0]
        pred = F.sigmoid(logits.astype("float32"))
        if labels is not None:
            labels_f = labels.astype("float32").reshape(pred.shape)
            loss = F.mse_loss(pred, labels_f)
            try:
                out.loss = loss
                out.logits = pred
                return out
            except Exception:
                return (loss, pred)
        try:
            out.logits = pred
            return out
        except Exception:
            return (pred,)

    model.forward = _bounded_forward
    logger.info("Wrapped model.forward with sigmoid + MSE for [0, 1] regression.")

    # ------------------------------------------------------------------
    # 3. Dataset (in-memory, tokenize on the fly)
    # ------------------------------------------------------------------
    sep = tokenizer.sep_token or "[SEP]"

    class CoverageDataset(Dataset):
        def __init__(self, df, max_len):
            self.src = df["src_fm"].astype(str).tolist()
            self.tgt = df["target"].astype(str).tolist()
            self.lab = df["condition_cover_rate"].astype(float).tolist()
            self.max_len = max_len

        def __len__(self):
            return len(self.lab)

        def __getitem__(self, i):
            text = f"{self.src[i]} {sep} {self.tgt[i]}"
            enc = tokenizer(
                text,
                truncation=True,
                max_length=self.max_len,
                return_attention_mask=True,
            )
            return {
                "input_ids": enc["input_ids"],
                "attention_mask": enc["attention_mask"],
                "labels": float(self.lab[i]),
            }

    train_ds = CoverageDataset(df_tr, args.max_seq_length)
    valid_ds = CoverageDataset(df_va, args.max_seq_length)

    data_collator = DataCollatorWithPadding(
        tokenizer=tokenizer,
        max_length=args.max_seq_length,
        return_tensors="pd",
    )

    # ------------------------------------------------------------------
    # 4. Trainer
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
        fp16=args.fp16,
        fp16_opt_level="O1",
        bf16=args.bf16,
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
        disable_tqdm=False,
    )

    def compute_metrics(eval_preds):
        preds, labels = eval_preds
        return _compute_regression_metrics(preds, labels)

    callbacks = [EarlyStoppingCallback(early_stopping_patience=3)]

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=valid_ds,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=callbacks,
    )

    # ------------------------------------------------------------------
    # 5. Train + evaluate
    # ------------------------------------------------------------------
    logger.info("Starting training ...")
    t0 = time.time()
    train_result = trainer.train()
    runtime_sec = time.time() - t0

    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))

    eval_metrics = trainer.evaluate()
    logger.info("Validation: %s", json.dumps(eval_metrics, indent=2))

    summary = {
        "framework": "paddlepaddle + paddlenlp",
        "base_model": args.base_model,
        "n_params_million": round(float(n_params), 1),
        "train_rows": len(train_ds),
        "valid_rows": len(valid_ds),
        "epochs": args.epochs,
        "effective_batch_size":
            args.batch_size * args.gradient_accumulation_steps,
        "max_seq_length": args.max_seq_length,
        "learning_rate": args.learning_rate,
        "lr_scheduler_type": args.lr_scheduler_type,
        "fp16": args.fp16,
        "bf16": args.bf16,
        "train_subsample": args.train_subsample,
        "train_runtime_sec": round(runtime_sec, 1),
        "validation_metrics": eval_metrics,
    }
    with open(out_dir / "training_metrics.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    logger.info("Wrote: %s", out_dir / "training_metrics.json")
    logger.info("Model saved to: %s", out_dir)


if __name__ == "__main__":
    main()
