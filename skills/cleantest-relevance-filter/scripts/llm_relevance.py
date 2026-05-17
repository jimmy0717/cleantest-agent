"""LLM-based relevance judgment for borderline test-focal pairs.

This module is used by the relevance filter when AST name matching
finds zero overlap. It asks the LLM to judge whether the test might
be indirectly testing the focal method.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.llm_client import llm_judge_relevance  # noqa: E402


def judge_single(src_fm: str, target: str, model: str = "gpt-4o-mini") -> str:
    """Judge relevance for a single sample.

    Args:
        src_fm: Focal method source code (Java).
        target: Test case source code (Java).
        model: LLM model name.

    Returns:
        "RELEVANT" or "IRRELEVANT"
    """
    return llm_judge_relevance(src_fm=src_fm, target=target, model=model)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="LLM relevance judgment for a single sample"
    )
    parser.add_argument("--src_fm", required=True, help="Focal method code")
    parser.add_argument("--target", required=True, help="Test case code")
    parser.add_argument("--model", default="gpt-4o-mini")
    args = parser.parse_args()

    result = judge_single(args.src_fm, args.target, args.model)
    print(f"Verdict: {result}")
