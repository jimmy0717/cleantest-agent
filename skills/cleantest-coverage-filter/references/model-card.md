# Model Card: Coverage Prediction GPT-2

## Model Details

| Property | Value |
|----------|-------|
| **Model Type** | GPT-2 for Sequence Classification (Regression) |
| **Base Model** | `openai-community/gpt2` (117M parameters) |
| **Task** | Predict branch coverage of a unit test given focal method + test code |
| **Output** | Single float ∈ [0, 1] representing predicted branch coverage |
| **Training Data** | Methods2Test dataset with `condition_cover_rate` labels |
| **Training Hardware** | Single NVIDIA RTX 3090/4090 (24GB VRAM) |
| **Training Time** | ~6 hours (3 epochs) |
| **Framework** | HuggingFace Transformers 4.35+ |

## Intended Use

This model predicts the likely branch coverage that a test case would achieve when executed against its focal method. It is used as Filter 3 in the CleanTest-Agent pipeline to remove test samples with predicted low coverage (default threshold: 0.3).

## Input Format

Concatenation of focal method and test case, separated by `[SEP]`:
```
public int add(int a, int b) { return a + b; } [SEP] @Test public void testAdd() { assertEquals(3, add(1, 2)); }
```

Maximum sequence length: 512 tokens.

## Limitations

- **Java only**: Trained exclusively on Java code from Methods2Test.
- **Predicted, not measured**: Coverage is estimated, not measured by actual execution.
- **Domain-specific**: Performance may degrade on code styles very different from the training distribution.
- **No GPU fallback**: Requires CUDA-capable GPU for reasonable inference speed. The pipeline gracefully skips this filter when no GPU is available.

## Ethical Considerations

This model is used purely for data quality filtering. It does not generate code or make security-sensitive decisions. Its predictions should be verified against actual coverage measurements when possible.

## How to Train

```bash
python skills/cleantest-coverage-filter/scripts/train_model.py \
  --train_csv path/to/data_with_coverage.csv \
  --output_model ./coverage_model \
  --epochs 3 --batch_size 16
```

## How to Use for Inference

```bash
python skills/cleantest-coverage-filter/scripts/coverage_predictor.py \
  --input_csv path/to/data.csv \
  --output_csv filtered.csv \
  --model_path ./coverage_model \
  --threshold 0.3
```
