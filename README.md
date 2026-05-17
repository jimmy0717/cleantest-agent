# CleanTest-Agent

> A Multi-Agent Skill-Orchestrated System for Unit Test Training Data Quality Assurance

[![CI](https://github.com/YOUR_USERNAME/cleantest-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/cleantest-agent/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

CleanTest-Agent transforms the [CleanTest](https://arxiv.org/abs/2502.14212) data cleaning pipeline (FSE 2025 Distinguished Paper) into a set of composable **Agent Skills** that can be orchestrated by coding assistants (CodeBuddy, Claude Code, Cursor, etc.).

It combines **rule-based static analysis** with **LLM-enhanced semantic judgment** and **model-driven coverage prediction** to remove noisy samples from unit test training datasets.

### Architecture

```
User → Orchestrator Skill (cleantest-pipeline)
              │
       ┌──────┼──────┐
       ▼      ▼      ▼
   Filter 1  Filter 2  Filter 3
   Syntax    Relevance  Coverage
   (Rules    (AST +     (GPT-2
   + LLM)    LLM)       Regression)
       │      │      │
       └──────┼──────┘
              ▼
        Clean Dataset
        + Noise Report
```

### Key Innovation

- **Model-Driven** approach (rules + ML model + LLM) vs **Pure-LLM** approach → higher F1, lower cost
- Only ~12.7% borderline samples require LLM calls → cost-effective
- Each filter is an independent, testable, reusable **Skill**

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Pipeline

```bash
python -m src.pipeline \
  --input_csv path/to/your/dataset.csv \
  --output_dir ./output \
  --llm_enhance
```

### 3. Install as CodeBuddy Skills

```bash
make install
# Or manually:
cp -R skills/* ~/.codebuddy/skills/
```

### 4. Run Tests

```bash
# Run all 38 tests with verbose output
python3 -m pytest tests/ -v --tb=short

# Run with coverage report
python3 -m pytest tests/ -v --cov=src --cov-report=term-missing

# Run a specific test file
python3 -m pytest tests/test_syntax_filter.py -v

# Or via Makefile
make test
```

**Expected output:**
```
tests/test_coverage_filter.py::TestCoverageFilter::test_removes_low_coverage PASSED
tests/test_coverage_filter.py::TestCoverageFilter::test_keeps_all_above_threshold PASSED
... (38 tests)
============================== 38 passed in 0.74s ==============================
```

**Test structure:**

| Test File | Cases | What It Tests |
|-----------|:-----:|---------------|
| `test_syntax_filter.py` | 14 | All 7 syntax noise types + annotation detection |
| `test_relevance_filter.py` | 7 | AST method extraction + name overlap calculation |
| `test_coverage_filter.py` | 4 | Coverage threshold logic + graceful skip |
| `test_pipeline.py` | 4 | End-to-end integration (noisy + clean fixtures) |
| `test_report.py` | 5 | JSON/Markdown report generation |

### 5. Run Experiments

```bash
# Generate rule-based ground truth labels (no API key needed)
python3 experiments/run_baselines.py \
  --input_csv path/to/all_train.csv --sample_size 500 --skip_llm

# Run simulated baseline comparison
python3 experiments/simulate_baselines.py

# Run real LLM baselines (requires OPENAI_API_KEY)
export OPENAI_API_KEY="sk-..."
python3 experiments/run_baselines.py \
  --input_csv path/to/all_train.csv --sample_size 500
```

## Code Assistant Usage

For detailed instructions on using CleanTest-Agent as Agent Skills in CodeBuddy, Claude Code, or Cursor, see **[docs/code-assistant-guide.md](docs/code-assistant-guide.md)**.

**Quick summary:**

1. Install skills: `make install` (copies to `~/.codebuddy/skills/`)
2. Restart CodeBuddy
3. Say: "Help me clean this unit test training dataset" — the assistant auto-invokes the pipeline skill

## Skill Descriptions

| Skill | Trigger Phrases |
|-------|----------------|
| `cleantest-pipeline` | "clean test data", "run cleantest", "filter noisy tests" |
| `cleantest-syntax-filter` | "check syntax noise", "detect noisy test syntax" |
| `cleantest-relevance-filter` | "check test relevance", "filter irrelevant tests" |
| `cleantest-coverage-filter` | "predict coverage", "filter low coverage tests" |

## Project Structure

```
cleantest-agent/
├── skills/                 # Agent Skills (SKILL.md + scripts)
├── src/                    # Shared library code
├── tests/                  # Unit & integration tests
├── experiments/            # Evaluation scripts & results
├── docs/                   # Design documents
├── .github/workflows/      # CI/CD
└── requirements.txt
```

## References

- Zhang et al., "Less is More: On the Importance of Data Quality for Unit Test Generation", FSE 2025 (Distinguished Paper Award)
- arXiv: [2502.14212](https://arxiv.org/abs/2502.14212)

## License

MIT License
