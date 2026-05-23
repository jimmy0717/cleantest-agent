---
name: cleantest-coverage-filter
description: >
  Filters unit test samples by branch coverage. Two modes: (a) label
  mode (default) reads ground-truth coverage from the input CSV's
  `condition_cover_rate` column; (b) model mode loads a fine-tuned
  Qwen2.5-Coder-0.5B regression model to predict coverage when no
  label is available. The original CleanTest paper used CodeGPT with
  threshold 0.01; we keep the same threshold (default 0.01).
  Triggers: "predict coverage", "filter low coverage tests",
  "coverage prediction", "预测覆盖率"
---

# Coverage Prediction Filter

## Prerequisites

This skill depends on the open-source [`cleantest-agent`](https://github.com/jimmy0717/cleantest-agent) Python package. Two installation tiers are supported:

```bash
# Label-mode only (uses the `condition_cover_rate` column in the input CSV;
# no GPU required; this is the path used to validate Filter 3 on
# 469,174 real samples in the published evaluation)
pip install cleantest-agent

# Model-mode (fine-tune / load a Qwen2.5-Coder-0.5B regression model;
# pulls torch + transformers + datasets + scipy + scikit-learn)
pip install "cleantest-agent[coverage]"
```

This skill ships two complementary code paths. **Label mode** (the
default) reads the `condition_cover_rate` column directly and applies
the threshold in $O(N)$ row scan, with no model load. **Model mode**
fine-tunes a small open-weights code language model (default:
[Qwen2.5-Coder-0.5B](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B), Alibaba Tongyi Lab) on
the LessIsMore-FSE2025 `filter_train.csv` to *predict* the branch
coverage of a test case when no ground-truth label is available, and
then applies the same threshold.

> **Status note.** The model-mode code path supports any
> HuggingFace causal-LM / encoder backbone via `Auto*` classes.
> Default base model is Qwen2.5-Coder-0.5B; alternatives that have
> been wired up but not benchmarked include DeepSeek-Coder-1.3B and
> the original GPT-2.

**Note**: The original CleanTest paper used CodeGPT (achieving MAE 7.98%, MSE 1.05%)
with a threshold of 0.01. Our model-mode default is Qwen2.5-Coder-0.5B (500M
parameters, 2024, code-specific pre-training) selected as a stronger and
more recent open-weights replacement for CodeGPT, with the same default
threshold of 0.01. In environments without a trained checkpoint or without
a GPU, the filter automatically falls back to **label mode**, which reads
the JaCoCo `condition_cover_rate` column directly from the input CSV.

## Model Details

| Property | Value |
|----------|-------|
| Default Base Model | `Qwen/Qwen2.5-Coder-0.5B` (500M params, 2024, Alibaba Tongyi Lab) |
| Original Paper Baseline | CodeGPT (MAE: 7.98%, MSE: 1.05%) |
| Task | Regression (SequenceClassification, num_labels=1) |
| Input | Concatenation of focal method + test case via `[SEP]` |
| Output | Predicted branch coverage |
| Threshold | 0.01 (configurable; same as original paper) |
| Recommended Hardware | Single NVIDIA V100 32 GB (e.g. Baidu PaddlePaddle AI Studio) |
| Training time (default config) | ~5--7 hours on V100 32 GB, 3 epochs, fp16 |
| Alternative backbones supported | `deepseek-ai/deepseek-coder-1.3b-base`, `openai-community/gpt2`, any other HF Hub `*ForSequenceClassification` model |

## Modes

### Label Mode (Default)

Reads JaCoCo ground-truth coverage from the input CSV's
`condition_cover_rate` column, applies the threshold in an $O(N)$ row
scan, and reports `low_coverage` removals. No model load, no GPU.

```bash
python skills/cleantest-coverage-filter/scripts/coverage_predictor.py \
  --input_csv <path_with_condition_cover_rate_column> \
  --output_csv <path> \
  --threshold 0.01
```

This is the path exercised by all Filter 3 numbers in the published
evaluation.

### Model Mode (Optional, requires a fine-tuned checkpoint)

Loads a fine-tuned regression model (any HuggingFace
`*ForSequenceClassification` checkpoint with `num_labels=1`) to
predict coverage when no label column is present.

```bash
python skills/cleantest-coverage-filter/scripts/coverage_predictor.py \
  --input_csv <path> \
  --output_csv <path> \
  --model_path <path_to_fine_tuned_checkpoint> \
  --threshold 0.01 \
  --batch_size 16
```

### Train Mode (Optional)

```bash
# 1. Stratified 80/10/10 split (preserves coverage distribution).
python skills/cleantest-coverage-filter/scripts/prepare_data.py \
  --input_csv path/to/filter_train.csv \
  --output_dir path/to/splits

# 2. Fine-tune Qwen2.5-Coder-0.5B (V100 32 GB, ~5-7 hours).
python skills/cleantest-coverage-filter/scripts/train_model.py \
  --base_model Qwen/Qwen2.5-Coder-0.5B \
  --train_csv path/to/splits/train.csv \
  --valid_csv path/to/splits/valid.csv \
  --output_model path/to/checkpoint \
  --epochs 3 --batch_size 8 --gradient_accumulation_steps 2 \
  --learning_rate 2e-5 --max_seq_length 512 --fp16

# 3. Held-out evaluation (MAE / MSE / RMSE / R^2 / Pearson / Spearman /
#    threshold-aware F1 of low-coverage detection).
python skills/cleantest-coverage-filter/scripts/evaluate_model.py \
  --input_csv path/to/splits/test.csv \
  --model_path path/to/checkpoint \
  --output_predictions path/to/splits/test_pred.csv \
  --threshold 0.01
```

A turn-key launcher for Baidu PaddlePaddle AI Studio (V100 32 GB) is
provided as
`scripts/train_qwen_baidu.sh`.

## Fallback

If no trained model is available or no GPU is present, this filter can be
skipped by passing `--skip_coverage` to the pipeline. The pipeline will
still apply Filter 1 (Syntax) and Filter 2 (Relevance).

## Scripts

- `scripts/prepare_data.py` --- Stratified 80/10/10 split helper
- `scripts/train_model.py` --- Fine-tune Qwen2.5-Coder-0.5B (or any HF backbone)
- `scripts/evaluate_model.py` --- Held-out test metrics (MAE / MSE / R^2 / corr / F1)
- `scripts/coverage_predictor.py` --- Inference script (label mode + model mode)
- `scripts/train_qwen_baidu.sh` --- Baidu AI Studio V100 32 GB launcher
- `references/model-card.md` --- Model documentation
