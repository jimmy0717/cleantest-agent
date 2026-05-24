---
name: cleantest-pipeline
description: >
  Orchestrates the CleanTest data cleaning pipeline for unit test training datasets.
  Sequentially invokes syntax-filter, relevance-filter, and coverage-filter skills
  to remove noisy samples, then generates a noise report.
  Triggers: "clean test data", "filter noisy tests", "run cleantest pipeline",
  "remove noisy samples", "data quality", "clean training data", "unit test cleaning",
  "数据清洗", "过滤噪声测试", "运行 CleanTest", "清洗训练数据"
---

# CleanTest Pipeline Orchestrator

## Prerequisites

This skill is the front-end of the open-source [`cleantest-agent`](https://github.com/jimmy0717/cleantest-agent) Python package. Before invoking it, make sure the package is installed in the active Python environment:

```bash
pip install cleantest-agent
# or, from a checkout of the project repository:
pip install -e .
```

If the package is missing, the helper scripts under this skill exit with a clear message and a one-line install hint.

You are orchestrating a 3-stage data cleaning pipeline for unit test training data.
The goal is to remove noisy samples that degrade model performance.

## Pipeline Stages

### Stage 1: Syntax Noise Filter
Invoke the `cleantest-syntax-filter` skill to detect and remove:
- Syntax errors (tree-sitter ERROR nodes)
- Empty exception handling statements (catch/finally with empty blocks)
- Missing implementation / empty functions (method body < 3 AST children)
- Ambiguous data types (generics markers like `<E>`, `<T>`, `<?>`)
- Unnecessary annotations (Aho-Corasick, 21,954 patterns)
- Non-English literals (Chinese/Japanese/Korean)

### Stage 2: Relevance Filter
Invoke the `cleantest-relevance-filter` skill to detect and remove:
- Test cases that have NO relevance to their focal method
- Uses AST-based matching: function name + parameter count + parameter types (fast path)
- Falls back to LLM semantic judgment for borderline cases

### Stage 3: Coverage Prediction Filter
Invoke the `cleantest-coverage-filter` skill to detect and remove:
- Test cases with branch coverage below threshold (default: 0.01)
- Uses ground-truth `condition_cover_rate` labels when present (label mode); falls back to a fine-tuned Qwen2.5-Coder-0.5B regression model when only raw code is available (model mode). The original CleanTest paper used CodeGPT, a continued-pretrained GPT-2 on code; Qwen2.5-Coder-0.5B is the modern code-specific replacement.

## Input Requirements

The input CSV must contain at minimum:
- `src_fm`: The focal method source code (Java)
- `target`: The unit test source code (Java)

Optional columns: `condition_cover_rate` (enables Filter 3 without model)

## Output

After all stages complete, generate:
1. `filtered_data.csv` -- Cleaned dataset (rows that passed all filters)
2. `noise_report.json` -- Structured report with per-filter statistics
3. `summary.md` -- Human-readable summary

## Execution

After installing the package (see Prerequisites), run:

```bash
cleantest \
  --input_csv <path> \
  --output_dir <path> \
  [--llm_enhance]            # Enable LLM enhancement for Filter 1 & 2
  [--coverage_threshold 0.01]
  [--skip_coverage]          # Skip Filter 3 if no GPU/labels available
  [--reflection]             # Enable reflective LLM step for Filter 2
```

Equivalent module form (works without `pip install`, but only inside a checkout):

```bash
python -m cleantest_agent.pipeline --input_csv <path> --output_dir <path>
```

## Checkpoints

After each filter stage, the pipeline logs:
- Number of samples removed
- Noise type breakdown
- Number of remaining samples

In CLI mode, the pipeline runs all stages automatically. When invoked through a coding assistant, intermediate results are reported to the user between stages.

## Error Handling

- **Malformed samples**: Wrapped in try/except, skipped silently without crashing.
- **Deep AST nesting**: Iterative stack-based traversal (no recursion).
- **Missing GPU/model**: Coverage filter gracefully skipped with `--skip_coverage`.
- **Missing API key**: LLM enhancement skipped, falls back to rules only.

## Scripts

- `cleantest_agent/pipeline.py` -- main orchestrator (exposed as the `cleantest` console script after install)
- `references/pipeline-schema.json` -- JSON Schema for input/output format
