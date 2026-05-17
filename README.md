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
make test
```

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
