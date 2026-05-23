"""Prepare a stratified train / valid / test split for Filter 3.

Reads the LessIsMore-FSE2025 ``filter_train.csv`` (or any CSV with
``src_fm`` + ``target`` + ``condition_cover_rate`` columns), drops
rows with missing values, sanity-checks the coverage label range,
then writes a reproducible 80/10/10 split stratified by the
quintile of ``condition_cover_rate``.

The stratification preserves the empirical coverage distribution
across all three splits, which matters for regression because a
random uniform split can put all extreme values into one bucket.

Usage::

    python prepare_data.py \
        --input_csv .../filter_train.csv \
        --output_dir .../data/coverage_splits \
        --train_ratio 0.8 --valid_ratio 0.1 --seed 42

Outputs (under ``--output_dir``)::

    train.csv  valid.csv  test.csv  split_summary.json
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
        description="Stratified split for Filter 3 coverage regression."
    )
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--train_ratio", type=float, default=0.8)
    parser.add_argument("--valid_ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--n_strata", type=int, default=5,
        help="Number of quantile buckets used for stratification. "
             "5 = quintiles (default).",
    )
    parser.add_argument(
        "--clip_label_max", type=float, default=1.0,
        help="Clip outlier labels above this value (the LessIsMore "
             "filter_train.csv contains a few rows with values up to "
             "~1.91 which is outside the JaCoCo [0,1] semantics; "
             "default clips them to 1.0).",
    )
    parser.add_argument(
        "--max_rows", type=int, default=None,
        help="Optional row cap (for quick smoke runs).",
    )
    args = parser.parse_args()

    if args.train_ratio + args.valid_ratio >= 1.0:
        logger.error("train_ratio + valid_ratio must leave room for test set.")
        sys.exit(2)

    try:
        import numpy as np
        import pandas as pd
    except ImportError:
        logger.error("pandas + numpy required. Install via pip install pandas numpy.")
        sys.exit(1)

    in_path = Path(args.input_csv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Reading %s", in_path)
    df = pd.read_csv(in_path, low_memory=False)
    logger.info("  Raw rows: %d", len(df))

    # ----- sanity / cleanup ----------------------------------------------------
    required = {"src_fm", "target", "condition_cover_rate"}
    missing = required - set(df.columns)
    if missing:
        logger.error("Missing required columns: %s", missing)
        sys.exit(2)

    n_before = len(df)
    df = df.dropna(subset=["src_fm", "target", "condition_cover_rate"])
    df["condition_cover_rate"] = pd.to_numeric(
        df["condition_cover_rate"], errors="coerce"
    )
    df = df.dropna(subset=["condition_cover_rate"])
    n_dropped_na = n_before - len(df)
    logger.info("  Dropped %d rows with missing/invalid labels", n_dropped_na)

    n_above_one = int((df["condition_cover_rate"] > 1.0).sum())
    n_below_zero = int((df["condition_cover_rate"] < 0.0).sum())
    if n_above_one > 0 or n_below_zero > 0:
        logger.warning(
            "  Found %d rows with coverage > 1.0 and %d with coverage < 0.0; "
            "clipping to [0, %.2f]",
            n_above_one, n_below_zero, args.clip_label_max,
        )
        df["condition_cover_rate"] = df["condition_cover_rate"].clip(
            lower=0.0, upper=args.clip_label_max,
        )

    df = df.drop_duplicates(subset=["target"], keep="first")
    logger.info("  After dedup on target: %d rows", len(df))

    if args.max_rows is not None and len(df) > args.max_rows:
        df = df.sample(n=args.max_rows, random_state=args.seed)
        logger.info("  Capped to %d rows (--max_rows)", len(df))

    # ----- stratified split ----------------------------------------------------
    df = df.reset_index(drop=True)
    quantiles = np.linspace(0.0, 1.0, args.n_strata + 1)
    bucket_edges = df["condition_cover_rate"].quantile(quantiles).values
    # Make edges strictly increasing to avoid duplicate-bin errors when many
    # samples share the same coverage value.
    eps = 1e-9
    for i in range(1, len(bucket_edges)):
        if bucket_edges[i] <= bucket_edges[i - 1]:
            bucket_edges[i] = bucket_edges[i - 1] + eps
    df["_stratum"] = pd.cut(
        df["condition_cover_rate"],
        bins=bucket_edges,
        labels=False,
        include_lowest=True,
    )
    df["_stratum"] = df["_stratum"].fillna(0).astype(int)

    rng = np.random.default_rng(args.seed)

    train_chunks, valid_chunks, test_chunks = [], [], []
    for stratum, group in df.groupby("_stratum", sort=True):
        n = len(group)
        idx = group.sample(frac=1.0, random_state=int(rng.integers(2**31))).index
        n_train = int(n * args.train_ratio)
        n_valid = int(n * args.valid_ratio)
        train_chunks.append(df.loc[idx[:n_train]])
        valid_chunks.append(df.loc[idx[n_train:n_train + n_valid]])
        test_chunks.append(df.loc[idx[n_train + n_valid:]])

    train = (
        __import__("pandas").concat(train_chunks)
        .drop(columns=["_stratum"]).reset_index(drop=True)
    )
    valid = (
        __import__("pandas").concat(valid_chunks)
        .drop(columns=["_stratum"]).reset_index(drop=True)
    )
    test = (
        __import__("pandas").concat(test_chunks)
        .drop(columns=["_stratum"]).reset_index(drop=True)
    )

    # ----- write splits --------------------------------------------------------
    train_path = out_dir / "train.csv"
    valid_path = out_dir / "valid.csv"
    test_path = out_dir / "test.csv"
    train.to_csv(train_path, index=False)
    valid.to_csv(valid_path, index=False)
    test.to_csv(test_path, index=False)
    logger.info("  Train: %d  -> %s", len(train), train_path)
    logger.info("  Valid: %d  -> %s", len(valid), valid_path)
    logger.info("  Test : %d  -> %s", len(test), test_path)

    # ----- summary -------------------------------------------------------------
    def _describe(name, frame):
        return {
            "name": name,
            "n_rows": int(len(frame)),
            "coverage": {
                "min": float(frame["condition_cover_rate"].min()),
                "median": float(frame["condition_cover_rate"].median()),
                "mean": float(frame["condition_cover_rate"].mean()),
                "max": float(frame["condition_cover_rate"].max()),
                "std": float(frame["condition_cover_rate"].std()),
            },
        }

    summary = {
        "input_csv": str(in_path),
        "seed": args.seed,
        "n_strata": args.n_strata,
        "ratios": {
            "train": args.train_ratio,
            "valid": args.valid_ratio,
            "test": round(1.0 - args.train_ratio - args.valid_ratio, 4),
        },
        "rows_dropped_na": n_dropped_na,
        "rows_clipped_above_one": n_above_one,
        "rows_clipped_below_zero": n_below_zero,
        "splits": [
            _describe("train", train),
            _describe("valid", valid),
            _describe("test", test),
        ],
    }
    with open(out_dir / "split_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    logger.info("Wrote summary: %s", out_dir / "split_summary.json")


if __name__ == "__main__":
    main()
