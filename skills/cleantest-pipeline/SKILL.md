---
name: cleantest-pipeline
description: >
  Orchestrates the CleanTest data cleaning pipeline for unit test training datasets.
  Sequentially invokes syntax-filter, relevance-filter, and coverage-filter skills
  to remove noisy samples, then generates a noise report.
  Triggers: "clean test data", "filter noisy tests", "run cleantest pipeline",
  "数据清洗", "过滤噪声测试", "运行 CleanTest"
---

# CleanTest Pipeline Orchestrator

You are orchestrating a 3-stage data cleaning pipeline for unit test training data.
The goal is to remove noisy samples that degrade model performance.

## Pipeline Stages

### Stage 1: Syntax Noise Filter
Invoke the `cleantest-syntax-filter` skill to detect and remove:
- Syntax errors (tree-sitter ERROR nodes)
- Empty exception handlers (catch/finally with empty blocks)
- Empty methods (method body < 3 AST children)
- Ambiguous types (generics without type bounds)
- Unnecessary annotations (noisy modifiers)
- Non-English literals (Chinese/Japanese/Korean)
- Synchronized keywords

### Stage 2: Relevance Filter
Invoke the `cleantest-relevance-filter` skill to detect and remove:
- Test cases that have NO relevance to their focal method
- Uses AST-based method name matching first (fast path)
- Falls back to LLM semantic judgment for borderline cases

### Stage 3: Coverage Prediction Filter
Invoke the `cleantest-coverage-filter` skill to detect and remove:
- Test cases with predicted branch coverage below threshold (default: 0.3)
- Uses a fine-tuned GPT-2 regression model

## Input Requirements

The input CSV must contain at minimum:
- `src_fm`: The focal method source code (Java)
- `target`: The unit test source code (Java)

Optional columns: `src_fm_fc`, `condition_cover_rate`, `line_cover_rate`

## Output

After all stages complete, generate:
1. `filtered_data.csv` — Cleaned dataset (rows that passed all filters)
2. `noise_report.json` — Structured report with per-filter statistics
3. `summary.md` — Human-readable summary

## Execution

```bash
python -m src.pipeline \
  --input_csv <path> \
  --output_dir <path> \
  [--llm_enhance]      # Enable LLM enhancement for Filter 1 & 2
  [--coverage_threshold 0.3]
  [--skip_coverage]    # Skip Filter 3 if no GPU available
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
