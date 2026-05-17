---
name: cleantest-coverage-filter
description: >
  Predicts branch coverage of unit tests using a fine-tuned GPT-2 regression
  model. Removes samples with predicted coverage below a configurable threshold.
  This is a pure model-driven filter.
  Triggers: "predict coverage", "filter low coverage tests",
  "coverage prediction", "预测覆盖率"
---

# Coverage Prediction Filter

This skill uses a fine-tuned GPT-2 regression model to predict the branch
coverage of a test case, filtering out low-coverage samples.

## Model Details

| Property | Value |
|----------|-------|
| Base Model | `openai-community/gpt2` (117M params) |
| Task | Regression (SequenceClassification, num_labels=1) |
| Input | Concatenation of focal method + test case |
| Output | Predicted branch coverage ∈ [0, 1] |
| Threshold | 0.3 (configurable) |
| Training Hardware | Single RTX 3090/4090 (~6 hours) |

## Modes

### Predict Mode (Default)
```bash
python skills/cleantest-coverage-filter/scripts/coverage_predictor.py \
  --input_csv <path> \
  --output_csv <path> \
  --model_path <path_to_trained_model> \
  --threshold 0.3
```

### Train Mode (Optional)
```bash
python skills/cleantest-coverage-filter/scripts/train_model.py \
  --train_csv <path_with_coverage_labels> \
  --output_model <path> \
  --epochs 3 \
  --batch_size 16
```

## Fallback

If no trained model is available or no GPU is present, this filter can be
skipped by passing `--skip_coverage` to the pipeline. The pipeline will
still apply Filter 1 (Syntax) and Filter 2 (Relevance).

## Scripts

- `scripts/coverage_predictor.py` — Inference script
- `scripts/train_model.py` — Training script
- `references/model-card.md` — Model documentation
