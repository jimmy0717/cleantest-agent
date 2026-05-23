"""Standalone syntax noise filter script.

Prerequisites:
    pip install cleantest-agent
    # or, from a clone of the repository:
    pip install -e .
"""

import argparse
import sys


def _check_install():
    try:
        from cleantest_agent.data_loader import load_csv, save_csv  # noqa: F401
        from cleantest_agent.pipeline import run_syntax_filter  # noqa: F401
        from cleantest_agent.report_generator import NoiseReport  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "ERROR: the `cleantest_agent` package is not installed.\n"
            "       Install it first via:\n"
            "         pip install cleantest-agent\n"
            "       or, from a checkout of the project:\n"
            "         pip install -e .\n"
        )
        sys.exit(2)


def main():
    _check_install()
    from cleantest_agent.data_loader import load_csv, save_csv
    from cleantest_agent.pipeline import run_syntax_filter
    from cleantest_agent.report_generator import NoiseReport

    parser = argparse.ArgumentParser(description="Syntax Noise Filter")
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--output_csv", required=True)
    parser.add_argument("--llm_enhance", action="store_true")
    args = parser.parse_args()

    df = load_csv(args.input_csv)
    df = df.drop_duplicates(subset=["target"], keep="first")

    report = NoiseReport(total_samples=len(df))
    remove_idx = run_syntax_filter(df, report, llm_enhance=args.llm_enhance)
    df = df.drop(index=remove_idx)

    report.finalize()
    save_csv(df, args.output_csv)
    print(f"Removed {len(remove_idx)} / {report.total_samples} samples")
    print(f"Breakdown: {report.breakdown}")


if __name__ == "__main__":
    main()
