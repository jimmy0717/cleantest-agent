"""Standalone coverage prediction filter script (Filter 3).

Two modes
---------
* **Label mode (default).**  Read the ground-truth
  ``condition_cover_rate`` column directly from the input CSV and
  apply the threshold in an O(N) row scan.  No model is loaded.
* **Model mode.**  Load a fine-tuned regression model checkpoint
  (default base model: ``Qwen/Qwen2.5-Coder-0.5B``) and predict
  branch coverage for each row, then apply the threshold.

Prerequisites
-------------
::

    pip install cleantest-agent              # core
    pip install cleantest-agent[coverage]    # adds torch + transformers

Inference, when the model checkpoint is local, additionally requires
``trust_remote_code=True`` for some Hub backbones (Qwen, DeepSeek).
"""

import argparse
import logging
import sys


def _check_install():
    try:
        from cleantest_agent.data_loader import load_csv, save_csv  # noqa: F401
        from cleantest_agent.report_generator import NoiseReport    # noqa: F401
    except ImportError:
        sys.stderr.write(
            "ERROR: the `cleantest_agent` package is not installed.\n"
            "       Install it first via:\n"
            "         pip install cleantest-agent\n"
            "       or, from a checkout of the project:\n"
            "         pip install -e .\n"
        )
        sys.exit(2)


def run_label_based_filter(df, report, threshold):
    """Filter using existing coverage labels in CSV (label mode)."""
    logger = logging.getLogger(__name__)
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


def run_model_based_filter(
    df, report, model_path, threshold,
    batch_size=16, max_length=512, fp16=True,
):
    """Filter using a fine-tuned regression model (model mode).

    Loads the checkpoint with HuggingFace Auto* classes so the same
    code path supports Qwen2.5-Coder, DeepSeek-Coder, GPT-2, and any
    other ``ForSequenceClassification`` model with num_labels=1.
    """
    logger = logging.getLogger(__name__)
    try:
        import torch
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )
    except ImportError:
        logger.error(
            "PyTorch / Transformers not installed. "
            "Install via: pip install cleantest-agent[coverage]"
        )
        return []

    if torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
        logger.warning("No GPU detected. Model inference will be slow.")

    logger.info("Loading model from %s on %s", model_path, device)
    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if (fp16 and device == "cuda") else torch.float32
    model = AutoModelForSequenceClassification.from_pretrained(
        model_path,
        torch_dtype=dtype,
        trust_remote_code=True,
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    model.eval().to(device)

    sep = tokenizer.sep_token or "[SEP]"
    remove = []
    n = len(df)
    indices = df.index.tolist()

    with torch.no_grad():
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            chunk = df.iloc[start:end]
            texts = [
                f"{(row.get('src_fm') or '')} {sep} {(row.get('target') or '')}"
                for _, row in chunk.iterrows()
            ]
            enc = tokenizer(
                texts,
                truncation=True,
                max_length=max_length,
                padding=True,
                return_tensors="pt",
            ).to(device)
            preds = model(**enc).logits.squeeze(-1).float().cpu().tolist()
            if isinstance(preds, float):
                preds = [preds]
            for offset, pred in enumerate(preds):
                if pred < threshold:
                    report.add_noise("low_coverage")
                    remove.append(indices[start + offset])

    return remove


def main():
    _check_install()
    from cleantest_agent.data_loader import load_csv, save_csv
    from cleantest_agent.report_generator import NoiseReport

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="Coverage Prediction Filter")
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--output_csv", required=True)
    parser.add_argument(
        "--threshold", type=float, default=0.01,
        help="Default 0.01 matches the original CleanTest paper.",
    )
    parser.add_argument(
        "--model_path", default=None,
        help="Path to a fine-tuned regression model checkpoint "
             "(e.g. a directory produced by train_model.py). "
             "If not provided, the script falls back to the "
             "`condition_cover_rate` column from the CSV (label mode).",
    )
    parser.add_argument(
        "--batch_size", type=int, default=16,
        help="Inference batch size (model mode only).",
    )
    parser.add_argument(
        "--max_length", type=int, default=512,
        help="Tokenizer max length (model mode only).",
    )
    parser.add_argument(
        "--no_fp16", dest="fp16", action="store_false", default=True,
        help="Disable fp16 inference (use fp32; ~2x slower on V100).",
    )
    args = parser.parse_args()

    df = load_csv(args.input_csv)
    df = df.drop_duplicates(subset=["target"], keep="first")
    report = NoiseReport(total_samples=len(df))

    if args.model_path:
        remove_idx = run_model_based_filter(
            df, report, args.model_path, args.threshold,
            batch_size=args.batch_size,
            max_length=args.max_length,
            fp16=args.fp16,
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
