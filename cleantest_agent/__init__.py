"""CleanTest-Agent: A Multi-Agent Skill-Orchestrated System
for Unit Test Training Data Quality Assurance.

Public API:
    from cleantest_agent import (
        run_pipeline, run_syntax_filter, run_relevance_filter,
        run_coverage_filter, NoiseReport, load_csv, save_csv,
        llm_confirm_syntax_noise, llm_judge_relevance,
    )
"""

# Single source of truth for the version is `pyproject.toml`;
# `__version__` is resolved at import time from the installed
# distribution metadata so the two cannot drift out of sync.
# Falls back to "0.0.0+unknown" only when the package is imported
# directly from a source tree that has never been `pip install`-ed
# (e.g. by running tests from a freshly cloned repo without pip);
# all CI / CD / PyPI / sigstore paths always go through an install.
try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    try:
        __version__ = _pkg_version("cleantest-agent")
    except PackageNotFoundError:
        __version__ = "0.0.0+unknown"
except ImportError:  # pragma: no cover - importlib.metadata is stdlib on 3.8+
    __version__ = "0.0.0+unknown"

from cleantest_agent.data_loader import load_csv, save_csv
from cleantest_agent.report_generator import NoiseReport
from cleantest_agent.pipeline import (
    run_pipeline,
    run_syntax_filter,
    run_relevance_filter,
    run_coverage_filter,
)
from cleantest_agent.llm_client import (
    llm_confirm_syntax_noise,
    llm_judge_relevance,
)

__all__ = [
    "__version__",
    # data
    "load_csv",
    "save_csv",
    # report
    "NoiseReport",
    # pipeline
    "run_pipeline",
    "run_syntax_filter",
    "run_relevance_filter",
    "run_coverage_filter",
    # llm
    "llm_confirm_syntax_noise",
    "llm_judge_relevance",
]
