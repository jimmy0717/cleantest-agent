"""CleanTest-Agent main pipeline: orchestrates 3 filter stages."""

import argparse
import logging
import sys
from pathlib import Path

from tqdm import tqdm

from src.data_loader import load_csv, save_csv
from src.parser_utils import (
    parse_java,
    detect_grammar_errors,
    detect_empty_exception,
    detect_empty_method,
    detect_ambiguous_type,
    detect_non_english,
    detect_synchronized,
    extract_src_methods,
    extract_test_invocations,
    compute_relevance,
)
from src.llm_client import llm_confirm_syntax_noise, llm_judge_relevance
from src.report_generator import NoiseReport

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Filter 1: Syntax Noise
# ---------------------------------------------------------------------------

def run_syntax_filter(
    df, report: NoiseReport, llm_enhance: bool = False
) -> list:
    """Filter 1: detect syntax noise.  Returns list of row indices to remove."""
    remove_indices = []

    for idx, row in tqdm(
        df.iterrows(), total=len(df), desc="Filter 1: Syntax"
    ):
        src_fm = str(row["src_fm"])
        target = str(row["target"])
        src_root = parse_java(src_fm)
        tgt_root = parse_java(target)

        noise_type = None

        # N4: Ambiguous type
        if detect_ambiguous_type(src_root):
            noise_type = "ambiguous_type"

        # N1: Syntax errors
        elif detect_grammar_errors(src_root) or detect_grammar_errors(tgt_root):
            noise_type = "syntax_error"

        # N2: Empty exception
        elif detect_empty_exception(src_root):
            noise_type = "empty_exception"

        # N3: Empty method
        elif detect_empty_method(src_root):
            noise_type = "empty_method"

        # N6: Non-English literals
        elif detect_non_english(src_fm) or detect_non_english(target):
            noise_type = "non_english"

        # N7: Synchronized
        elif detect_synchronized(src_fm):
            noise_type = "synchronized"

        if noise_type:
            # Optional LLM confirmation for borderline cases
            if llm_enhance and noise_type in ("syntax_error", "empty_method"):
                report.llm_calls += 1
                verdict = llm_confirm_syntax_noise(
                    code=src_fm,
                    noise_type=noise_type,
                    rule_result=f"Detected {noise_type} in focal method",
                )
                if verdict == "KEEP":
                    report.llm_overrides += 1
                    continue  # LLM overrode → keep this sample

            report.add_noise(noise_type)
            remove_indices.append(idx)

    return remove_indices


# ---------------------------------------------------------------------------
# Filter 2: Relevance
# ---------------------------------------------------------------------------

def run_relevance_filter(
    df, report: NoiseReport, llm_enhance: bool = False
) -> list:
    """Filter 2: detect irrelevant test-focal pairs. Returns indices to remove."""
    remove_indices = []

    for idx, row in tqdm(
        df.iterrows(), total=len(df), desc="Filter 2: Relevance"
    ):
        src_fm = str(row["src_fm"])
        target = str(row["target"])

        src_root = parse_java(src_fm)
        tgt_root = parse_java(target)

        src_methods = extract_src_methods(src_root)
        test_invocations = extract_test_invocations(tgt_root)
        overlap = compute_relevance(src_methods, test_invocations)

        if overlap == 0:
            # Stage B: LLM semantic judgment
            if llm_enhance:
                report.llm_calls += 1
                verdict = llm_judge_relevance(src_fm=src_fm, target=target)
                if verdict == "RELEVANT":
                    report.llm_overrides += 1
                    continue  # LLM says relevant → keep

            report.add_noise("no_relevance")
            remove_indices.append(idx)

    return remove_indices


# ---------------------------------------------------------------------------
# Filter 3: Coverage (stub - requires trained model)
# ---------------------------------------------------------------------------

def run_coverage_filter(
    df, report: NoiseReport, threshold: float = 0.3
) -> list:
    """Filter 3: remove low-coverage samples.

    If the CSV has a `condition_cover_rate` column, use ground-truth labels.
    Otherwise, this filter is skipped (model inference requires GPU + weights).
    """
    if "condition_cover_rate" not in df.columns:
        logger.warning(
            "Column 'condition_cover_rate' not found. "
            "Skipping coverage filter. Use --skip_coverage or provide "
            "coverage labels."
        )
        return []

    remove_indices = []
    for idx, row in tqdm(
        df.iterrows(), total=len(df), desc="Filter 3: Coverage"
    ):
        coverage = float(row["condition_cover_rate"])
        if coverage < threshold:
            report.add_noise("low_coverage")
            remove_indices.append(idx)

    return remove_indices


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    input_csv: str,
    output_dir: str,
    llm_enhance: bool = False,
    skip_coverage: bool = False,
    coverage_threshold: float = 0.3,
):
    """Run the full CleanTest-Agent pipeline."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load data
    logger.info(f"Loading dataset: {input_csv}")
    df = load_csv(input_csv)
    df = df.drop_duplicates(subset=["target"], keep="first")
    logger.info(f"Loaded {len(df)} unique samples")

    report = NoiseReport(total_samples=len(df))

    # Stage 1: Syntax Filter
    logger.info("=" * 60)
    logger.info("Stage 1: Syntax Noise Filter")
    logger.info("=" * 60)
    syntax_remove = run_syntax_filter(df, report, llm_enhance=llm_enhance)
    df = df.drop(index=syntax_remove)
    logger.info(
        f"  Removed {len(syntax_remove)} samples. "
        f"Remaining: {len(df)}"
    )

    # Stage 2: Relevance Filter
    logger.info("=" * 60)
    logger.info("Stage 2: Relevance Filter")
    logger.info("=" * 60)
    # Reset index after Stage 1 drops
    df = df.reset_index(drop=True)
    relevance_remove = run_relevance_filter(
        df, report, llm_enhance=llm_enhance
    )
    df = df.drop(index=relevance_remove)
    logger.info(
        f"  Removed {len(relevance_remove)} samples. "
        f"Remaining: {len(df)}"
    )

    # Stage 3: Coverage Filter
    if not skip_coverage:
        logger.info("=" * 60)
        logger.info("Stage 3: Coverage Prediction Filter")
        logger.info("=" * 60)
        df = df.reset_index(drop=True)
        coverage_remove = run_coverage_filter(
            df, report, threshold=coverage_threshold
        )
        df = df.drop(index=coverage_remove)
        logger.info(
            f"  Removed {len(coverage_remove)} samples. "
            f"Remaining: {len(df)}"
        )
    else:
        logger.info("Stage 3: Skipped (--skip_coverage)")

    # Finalize
    report.finalize()

    # Save outputs
    filtered_path = save_csv(df, output_path / "filtered_data.csv")
    json_path = report.to_json(output_path / "noise_report.json")
    md_path = report.to_markdown(output_path / "summary.md")

    logger.info("=" * 60)
    logger.info("Pipeline Complete!")
    logger.info(f"  Filtered data: {filtered_path}")
    logger.info(f"  Noise report:  {json_path}")
    logger.info(f"  Summary:       {md_path}")
    logger.info(
        f"  Total: {report.total_samples} → {report.kept_samples} "
        f"({report.removal_rate:.2%} removed)"
    )
    logger.info(f"  LLM calls: {report.llm_calls}, "
                f"overrides: {report.llm_overrides}")
    logger.info("=" * 60)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="CleanTest-Agent: Unit Test Data Cleaning Pipeline"
    )
    parser.add_argument(
        "--input_csv", required=True, help="Path to input CSV dataset"
    )
    parser.add_argument(
        "--output_dir", default="./output", help="Output directory"
    )
    parser.add_argument(
        "--llm_enhance", action="store_true",
        help="Enable LLM enhancement for Filter 1 & 2"
    )
    parser.add_argument(
        "--skip_coverage", action="store_true",
        help="Skip Filter 3 (coverage prediction)"
    )
    parser.add_argument(
        "--coverage_threshold", type=float, default=0.3,
        help="Coverage threshold for Filter 3 (default: 0.3)"
    )
    args = parser.parse_args()

    run_pipeline(
        input_csv=args.input_csv,
        output_dir=args.output_dir,
        llm_enhance=args.llm_enhance,
        skip_coverage=args.skip_coverage,
        coverage_threshold=args.coverage_threshold,
    )


if __name__ == "__main__":
    main()
