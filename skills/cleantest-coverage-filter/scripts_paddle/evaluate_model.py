"""Held-out evaluation for the Paddle-trained Filter 3 model.

Loads ``--model_path`` plus a CSV with ``condition_cover_rate``,
runs batched inference, and writes ``test_metrics.json`` next to
``--output_predictions``.
"""

import argparse
import json
import logging
import math
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--output_predictions", required=True)
    parser.add_argument("--threshold", type=float, default=0.01)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--max_seq_length", type=int, default=384)
    args = parser.parse_args()

    try:
        import numpy as np
        import paddle
        import pandas as pd
        from paddlenlp.transformers import (
            AutoTokenizer,
            Qwen2ForSequenceClassification,
        )
    except ImportError as e:
        logger.error("Missing dep: %s", e)
        sys.exit(1)

    device = "gpu" if paddle.device.is_compiled_with_cuda() else "cpu"
    paddle.device.set_device(device)
    logger.info("Device: %s", device)

    df = pd.read_csv(args.input_csv)
    needed = {"src_fm", "target", "condition_cover_rate"}
    missing = needed - set(df.columns)
    if missing:
        logger.error("Missing: %s", missing)
        sys.exit(2)
    df = df.dropna(subset=list(needed)).reset_index(drop=True)
    logger.info("Eval rows: %d", len(df))

    tokenizer = AutoTokenizer.from_pretrained(args.model_path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = Qwen2ForSequenceClassification.from_pretrained(
        args.model_path, num_labels=1, problem_type="regression",
        dtype="float16" if device == "gpu" else "float32",
        convert_from_torch=True,
    )
    model.eval()

    # Mirror the sigmoid wrap from training so predictions stay in [0, 1].
    import paddle.nn.functional as F

    sep = tokenizer.sep_token or "[SEP]"
    preds = []
    bs = args.batch_size
    n = len(df)

    with paddle.no_grad():
        for i in range(0, n, bs):
            chunk = df.iloc[i:i + bs]
            texts = [
                f"{r.src_fm} {sep} {r.target}"
                for r in chunk.itertuples(index=False)
            ]
            enc = tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=args.max_seq_length,
                return_attention_mask=True,
                return_tensors="pd",
            )
            out = model(**enc)
            logits = out.logits if hasattr(out, "logits") else out[0]
            pred = F.sigmoid(logits.astype("float32"))
            preds.extend(pred.numpy().reshape(-1).tolist())

            if (i // bs) % 50 == 0:
                logger.info("  %d / %d", min(i + bs, n), n)

    preds = np.asarray(preds, dtype=np.float64)
    labels = df["condition_cover_rate"].astype(float).clip(0.0, 1.0).to_numpy()

    # ----- Regression metrics -----
    mae = float(np.mean(np.abs(preds - labels)))
    mse = float(np.mean((preds - labels) ** 2))
    rmse = float(math.sqrt(mse))
    ss_res = float(np.sum((labels - preds) ** 2))
    ss_tot = float(np.sum((labels - labels.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else float("nan")

    metrics = {
        "n": int(len(labels)),
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2": r2,
    }
    try:
        from scipy.stats import pearsonr, spearmanr
        if labels.std() > 1e-9 and preds.std() > 1e-9:
            metrics["pearson_r"] = float(pearsonr(preds, labels)[0])
            metrics["spearman_rho"] = float(spearmanr(preds, labels)[0])
    except ImportError:
        pass

    # ----- Threshold-aware classification (low coverage <= threshold) -----
    yt = (labels <= args.threshold).astype(int)
    yp = (preds <= args.threshold).astype(int)
    tp = int(((yp == 1) & (yt == 1)).sum())
    fp = int(((yp == 1) & (yt == 0)).sum())
    fn = int(((yp == 0) & (yt == 1)).sum())
    tn = int(((yp == 0) & (yt == 0)).sum())
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    metrics["threshold"] = args.threshold
    metrics["precision"] = prec
    metrics["recall"] = rec
    metrics["f1"] = f1
    metrics["confusion"] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn}

    # ----- Write outputs -----
    out_pred_path = Path(args.output_predictions)
    out_pred_path.parent.mkdir(parents=True, exist_ok=True)
    pred_df = df[["src_fm", "target", "condition_cover_rate"]].copy()
    pred_df["pred_coverage"] = preds
    pred_df.to_csv(out_pred_path, index=False)

    out_metrics_path = out_pred_path.parent / "test_metrics.json"
    with open(out_metrics_path, "w") as fh:
        json.dump(metrics, fh, indent=2)

    logger.info("Predictions: %s", out_pred_path)
    logger.info("Metrics    : %s", out_metrics_path)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
