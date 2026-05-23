"""Held-out evaluation of a trained Filter 3 regression model.

Loads ``model_path`` plus ``test.csv`` (must contain
``condition_cover_rate``), runs batched inference, and writes
``test_metrics.json`` next to ``--output_predictions``.

Reported metrics (per the original CleanTest paper's MAE/MSE
convention plus standard regression diagnostics):

* MAE   --- Mean Absolute Error
* MSE   --- Mean Squared Error
* RMSE  --- Root MSE
* R^2   --- Coefficient of determination
* Pearson r and Spearman rho   --- rank/linear correlation
* CleanTest threshold-aware metrics:
    - precision / recall / F1 of "low coverage" classification at a
      given threshold (default 0.01) using the predicted vs.
      ground-truth labels.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a trained Filter 3 coverage regression model."
    )
    parser.add_argument("--input_csv", required=True,
                        help="Held-out test CSV (must contain condition_cover_rate).")
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--output_predictions", required=True,
                        help="Where to write per-row predictions as CSV.")
    parser.add_argument("--threshold", type=float, default=0.01)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--max_length", type=int, default=512)
    parser.add_argument("--no_fp16", dest="fp16", action="store_false", default=True)
    args = parser.parse_args()

    try:
        import numpy as np
        import pandas as pd
        import torch
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )
    except ImportError as e:
        logger.error("Missing dep: %s. Run pip install cleantest-agent[coverage] datasets scipy scikit-learn", e)
        sys.exit(1)

    device = (
        "cuda" if torch.cuda.is_available()
        else "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        else "cpu"
    )
    logger.info("Device: %s", device)

    df = pd.read_csv(args.input_csv, low_memory=False)
    df = df.dropna(subset=["src_fm", "target", "condition_cover_rate"])
    df["condition_cover_rate"] = pd.to_numeric(df["condition_cover_rate"], errors="coerce")
    df = df.dropna(subset=["condition_cover_rate"]).reset_index(drop=True)
    logger.info("Test rows: %d", len(df))

    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.float16 if (args.fp16 and device == "cuda") else torch.float32
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_path, torch_dtype=dtype, trust_remote_code=True,
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    model.eval().to(device)

    sep = tokenizer.sep_token or "[SEP]"

    preds = []
    with torch.no_grad():
        for start in range(0, len(df), args.batch_size):
            chunk = df.iloc[start:start + args.batch_size]
            texts = [
                f"{r['src_fm']} {sep} {r['target']}"
                for _, r in chunk.iterrows()
            ]
            enc = tokenizer(
                texts, truncation=True, max_length=args.max_length,
                padding=True, return_tensors="pt",
            ).to(device)
            out = model(**enc).logits.squeeze(-1).float().cpu().tolist()
            if isinstance(out, float):
                out = [out]
            preds.extend(out)

    labels = df["condition_cover_rate"].astype(float).tolist()
    p = np.array(preds, dtype=np.float64)
    y = np.array(labels, dtype=np.float64)

    # Regression metrics
    mae = float(np.mean(np.abs(p - y)))
    mse = float(np.mean((p - y) ** 2))
    rmse = float(np.sqrt(mse))
    ss_res = float(np.sum((y - p) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    metrics = {
        "n_rows": int(len(df)),
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2": r2,
    }
    try:
        from scipy.stats import pearsonr, spearmanr
        metrics["pearson_r"] = float(pearsonr(p, y)[0])
        metrics["spearman_rho"] = float(spearmanr(p, y)[0])
    except ImportError:
        pass

    # Threshold-aware classification (low-coverage detection)
    pred_low = p < args.threshold
    true_low = y < args.threshold
    tp = int((pred_low & true_low).sum())
    fp = int((pred_low & ~true_low).sum())
    fn = int((~pred_low & true_low).sum())
    tn = int((~pred_low & ~true_low).sum())
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    metrics["threshold"] = args.threshold
    metrics["confusion"] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn}
    metrics["precision_low"] = prec
    metrics["recall_low"] = rec
    metrics["f1_low"] = f1

    # Persist predictions + metrics
    out_pred = Path(args.output_predictions)
    out_pred.parent.mkdir(parents=True, exist_ok=True)
    df_out = df.copy()
    df_out["predicted_cover_rate"] = p
    df_out.to_csv(out_pred, index=False)
    metrics_path = out_pred.with_name("test_metrics.json")
    with open(metrics_path, "w") as fh:
        json.dump(metrics, fh, indent=2)

    logger.info("Predictions: %s", out_pred)
    logger.info("Metrics:     %s", metrics_path)
    logger.info("Summary:     %s", json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
