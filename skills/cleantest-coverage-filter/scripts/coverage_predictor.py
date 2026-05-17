"""Standalone coverage prediction filter script."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.data_loader import load_csv, save_csv
from src.pipeline import run_coverage_filter
from src.report_generator import NoiseReport


def main():
    parser = argparse.ArgumentParser(description="Coverage Prediction Filter")
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--output_csv", required=True)
    parser.add_argument("--threshold", type=float, default=0.3)
    args = parser.parse_args()

    df = load_csv(args.input_csv)
    df = df.drop_duplicates(subset=["target"], keep="first")

    report = NoiseReport(total_samples=len(df))
    remove_idx = run_coverage_filter(df, report, threshold=args.threshold)
    df = df.drop(index=remove_idx)

    report.finalize()
    save_csv(df, args.output_csv)
    print(f"Removed {len(remove_idx)} / {report.total_samples} samples")
    print(f"Breakdown: {report.breakdown}")


if __name__ == "__main__":
    main()
