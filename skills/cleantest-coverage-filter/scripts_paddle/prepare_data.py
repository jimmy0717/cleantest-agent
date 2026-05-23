"""Prepare a stratified train/valid/test split for Filter 3 (Paddle version).

Same logic as the PyTorch version: 80/10/10 split stratified by quintile
of ``condition_cover_rate``.  Pure pandas + numpy, no framework dependency.
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--train_ratio", type=float, default=0.8)
    parser.add_argument("--valid_ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    try:
        import numpy as np
        import pandas as pd
    except ImportError:
        logger.error("pandas / numpy not installed.")
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading: %s", args.input_csv)
    df = pd.read_csv(args.input_csv)

    needed = {"src_fm", "target", "condition_cover_rate"}
    missing = needed - set(df.columns)
    if missing:
        logger.error("Missing columns: %s", missing)
        sys.exit(2)

    before = len(df)
    df = df.dropna(subset=["src_fm", "target", "condition_cover_rate"])
    logger.info("Dropped %d rows with NaN. Remaining: %d", before - len(df), len(df))

    rate = df["condition_cover_rate"].astype(float)
    if rate.min() < 0 or rate.max() > 1.0:
        logger.warning(
            "condition_cover_rate range [%.3f, %.3f] outside [0, 1].",
            rate.min(), rate.max(),
        )

    # Stratify by quintile
    df["_bucket"] = pd.qcut(rate, q=5, labels=False, duplicates="drop")

    rng = np.random.default_rng(args.seed)
    train_parts, valid_parts, test_parts = [], [], []
    for b, sub in df.groupby("_bucket"):
        idx = np.arange(len(sub))
        rng.shuffle(idx)
        n_train = int(len(sub) * args.train_ratio)
        n_valid = int(len(sub) * args.valid_ratio)
        train_parts.append(sub.iloc[idx[:n_train]])
        valid_parts.append(sub.iloc[idx[n_train:n_train + n_valid]])
        test_parts.append(sub.iloc[idx[n_train + n_valid:]])

    import pandas as pd  # noqa
    train = pd.concat(train_parts).drop(columns=["_bucket"]).sample(
        frac=1.0, random_state=args.seed,
    ).reset_index(drop=True)
    valid = pd.concat(valid_parts).drop(columns=["_bucket"]).reset_index(drop=True)
    test = pd.concat(test_parts).drop(columns=["_bucket"]).reset_index(drop=True)

    train.to_csv(out_dir / "train.csv", index=False)
    valid.to_csv(out_dir / "valid.csv", index=False)
    test.to_csv(out_dir / "test.csv", index=False)

    summary = {
        "input_csv": args.input_csv,
        "seed": args.seed,
        "n_total": int(before),
        "n_after_dropna": int(len(df)),
        "n_train": int(len(train)),
        "n_valid": int(len(valid)),
        "n_test": int(len(test)),
        "label_min": float(rate.min()),
        "label_max": float(rate.max()),
        "label_mean": float(rate.mean()),
    }
    with open(out_dir / "split_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    logger.info("Wrote splits to %s", out_dir)
    logger.info("  train: %d  valid: %d  test: %d",
                len(train), len(valid), len(test))


if __name__ == "__main__":
    main()
