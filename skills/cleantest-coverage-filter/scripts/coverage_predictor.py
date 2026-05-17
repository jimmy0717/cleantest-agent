"""Standalone coverage prediction filter script.

Supports two modes:
- Label mode (default): use existing `condition_cover_rate` column in CSV
- Model mode: load a trained GPT-2 model to predict coverage (requires GPU)
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.data_loader import load_csv, save_csv
from src.report_generator import NoiseReport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_label_based_filter(df, report, threshold):
    """Filter using existing coverage labels in CSV."""
    if "condition_cover_rate" not in df.columns:
        logger.error(
            "No 'condition_cover_rate' column found. "
            "Provide a CSV with coverage labels or use --model_path."
        )
        return []
    remove = []
    for idx, row in df.iterrows():
        if float(row["condition_cover_rate"]) < threshold:
            report.add_noise("low_coverage")
            remove.append(idx)
    return remove


def run_model_based_filter(df, report, model_path, threshold):
    """Filter using a trained GPT-2 model for coverage prediction."""
    try:
        import torch
        from transformers import GPT2ForSequenceClassification, GPT2Tokenizer
    except ImportError:
        logger.error("PyTorch/Transformers not installed. pip install torch transformers")
        return []

    if not torch.cuda.is_available():
        logger.warning("No GPU detected. Model inference will be slow.")

    logger.info(f"Loading model from {model_path}")
    tokenizer = GPT2Tokenizer.from_pretrained(model_path)
    model = GPT2ForSequenceClassification.from_pretrained(model_path)
    model.eval()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    remove = []
    for idx, row in df.iterrows():
        text = f"{row['src_fm']} [SEP] {row['target']}"
        inputs = tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512
        ).to(device)
        with torch.no_grad():
            output = model(**inputs)
        predicted_coverage = output.logits.item()
        if predicted_coverage < threshold:
            report.add_noise("low_coverage")
            remove.append(idx)
    return remove


def main():
    parser = argparse.ArgumentParser(description="Coverage Prediction Filter")
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--output_csv", required=True)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument(
        "--model_path", default=None,
        help="Path to trained GPT-2 model. If not provided, uses "
             "'condition_cover_rate' column from CSV."
    )
    args = parser.parse_args()

    df = load_csv(args.input_csv)
    df = df.drop_duplicates(subset=["target"], keep="first")
    report = NoiseReport(total_samples=len(df))

    if args.model_path:
        remove_idx = run_model_based_filter(
            df, report, args.model_path, args.threshold
        )
    else:
        remove_idx = run_label_based_filter(df, report, args.threshold)

    df = df.drop(index=remove_idx)
    report.finalize()
    save_csv(df, args.output_csv)
    print(f"Removed {len(remove_idx)} / {report.total_samples} samples")
    print(f"Breakdown: {report.breakdown}")


if __name__ == "__main__":
    main()
