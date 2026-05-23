"""CleanTest-Agent: A Multi-Agent Skill-Orchestrated System
for Unit Test Training Data Quality Assurance.

Public API:
    from cleantest_agent import (
        run_pipeline, run_syntax_filter, run_relevance_filter,
        run_coverage_filter, NoiseReport, load_csv, save_csv,
        llm_confirm_syntax_noise, llm_judge_relevance,
    )
"""

__version__ = "0.1.0"

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
