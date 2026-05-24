"""Single-sample LLM relevance judgement.

Prerequisites:
    pip install cleantest-agent
    # or, from a clone of the repository:
    pip install -e .

Required environment variables:
    OPENAI_API_KEY        -- your API key
    OPENAI_BASE_URL       -- endpoint, e.g. https://api.deepseek.com/v1
                            (any OpenAI-compatible service works)
"""

import argparse
import sys


def _check_install():
    try:
        from cleantest_agent.llm_client import llm_judge_relevance  # noqa: F401
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
    from cleantest_agent.llm_client import llm_judge_relevance

    parser = argparse.ArgumentParser(description="Single-sample LLM relevance judgement")
    parser.add_argument("--src_fm", required=True, help="Focal method source code")
    parser.add_argument("--target", required=True, help="Test case source code")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--reflection", action="store_true",
                        help="Apply 5-rule reflection step on borderline cases")
    args = parser.parse_args()

    verdict = llm_judge_relevance(
        src_fm=args.src_fm,
        target=args.target,
        model=args.model,
        reflection=args.reflection,
    )
    print(verdict)


if __name__ == "__main__":
    main()
