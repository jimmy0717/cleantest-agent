# Model Card: Filter 3 Coverage Regression (Qwen2.5-Coder-0.5B)

> This card describes the base model and training recipe used for the
> model-mode code path of the `cleantest-coverage-filter` skill. The
> training script supports two backends:
>
> - `scripts/` — PyTorch + HuggingFace Transformers, used on V100 32 GB
>   with `fp16`.
> - `scripts_paddle/` — PaddlePaddle + PaddleNLP, used on A800 80 GB
>   with `bf16`. This is the variant that produced the held-out metrics
>   reported in `report/main.tex`, Section 7.5.
>
> Held-out test metrics are recorded in
> `experiments/results/coverage_run/test_metrics.json`. When that file
> is missing, the skill falls back to label mode, which performs an
> $O(N)$ row scan over the JaCoCo ground-truth labels and is what all
> reported Filter 3 numbers in earlier sections of the paper come from.

## Base model and training recipe

| Property | Value |
|----------|-------|
| Base model | `Qwen/Qwen2.5-Coder-0.5B` (Alibaba Tongyi Lab, 2024) |
| Parameters | ~494 M |
| Architecture | Qwen2 decoder-only causal LM, used via `Qwen2ForSequenceClassification` with `num_labels=1` for regression |
| Code-specific pre-training | Yes (Qwen2.5-Coder series) |
| Task | Predict branch coverage (`condition_cover_rate` from JaCoCo) of a unit test given focal method + test code |
| Output | A single float in [0, 1] (sigmoid-wrapped) |
| Training data | LessIsMore-FSE2025 `filter_train.csv` (469,174 rows), stratified 80/10/10 split by coverage quintile, seed 42 |
| Hardware (PaddlePaddle path) | NVIDIA A800 80 GB on Baidu PaddlePaddle AI Studio |
| Hardware (PyTorch path) | NVIDIA V100 32 GB |
| Mixed precision | bf16 on A800, fp16 on V100 |
| Effective batch size | 32 on A800, 16 on V100 |
| Max sequence length | 512 tokens on A800, 384 on V100 |
| Optimiser | AdamW, lr 2e-5 cosine, weight decay 0.01, warmup ratio 0.05 |
| Epochs | 2 |
| Original paper baseline | CodeGPT, MAE 7.98 %, MSE 1.05 % (Zhang et al., FSE 2025) |

The forward pass is wrapped to apply a sigmoid before the MSE loss so
that the regression output stays inside the same [0, 1] range as the
training labels. This is also the value that the inference script
returns, so no post-hoc scaling is needed at evaluation time.

## Why Qwen2.5-Coder-0.5B (and not GPT-2 / a 7B+ model)

The original CleanTest paper used **CodeGPT**, a continued-pretrained
GPT-2 (117M) on code. CodeGPT itself is no longer maintained on the
HuggingFace Hub at a stable identifier. We replace it with a stronger
modern open-weights small code model:

* **Qwen2.5-Coder-0.5B** (2024, Alibaba Tongyi Lab): code-specific
  pre-training on a large recent corpus, SOTA among open-weights
  small code models on HumanEval-Java / MBPP-Java; 500M parameters
  fit comfortably into V100 32 GB for full fine-tuning (no need for
  LoRA, which is unstable for a single-scalar regression head).

We deliberately avoid 7B+ backbones (DeepSeek-Coder-6.7B,
CodeFuse-13B, Qwen2.5-Coder-14B, etc.) because:

1. Branch coverage is a low-dimensional regression target; 7B+
   capacity is unnecessary and risks over-fitting on 469K rows.
2. 7B+ models on V100 32 GB require LoRA (training only ~1% of
   parameters), which is empirically unstable for a single-scalar
   regression head.
3. The whole point of Filter 3 in the model-driven philosophy is
   *"use the smallest model that adequately solves the subtask"*.

The training script (`scripts/train_model.py`) accepts any
HuggingFace `*ForSequenceClassification` backbone via
`--base_model`, so users can swap in DeepSeek-Coder-1.3B,
the original GPT-2, or other small code models for ablation.

## Intended Use

This model predicts the likely branch coverage that a test case
would achieve when executed against its focal method, serving as
Filter 3's optional model-mode in the CleanTest-Agent pipeline
(default threshold: 0.01, matching the original CleanTest paper).
When a ground-truth `condition_cover_rate` column is available,
Filter 3 prefers label mode and bypasses this model entirely.

## Input Format

Concatenation of focal method and test case, separated by the
tokenizer's `sep_token` (or the literal string `[SEP]` when the
tokenizer does not define one):

```
public int add(int a, int b) { return a + b; } [SEP] @Test public void testAdd() { assertEquals(3, add(1, 2)); }
```

Maximum sequence length: 512 tokens (configurable).

## Limitations

- **Java only**: Trained exclusively on Java code from Methods2Test.
- **Predicted, not measured**: Coverage is estimated, not measured by actual execution.
- **Domain-specific**: Performance may degrade on code styles very different from the training distribution.
- **Decoder-only on a regression task**: We follow the original CleanTest paper in using a causal LM as the backbone (CodeGPT was likewise decoder-only). An encoder backbone such as UniXcoder-base may achieve lower MAE/MSE on the same data; this is left as future work.
- **No GPU fallback**: Inference on CPU is feasible but slow for the full Methods2Test scale; the pipeline gracefully skips this filter when neither GPU nor labels are available.

## Ethical Considerations

This model is used purely for data quality filtering. It does not
generate code or make security-sensitive decisions. Its predictions
should be verified against actual coverage measurements when
possible.

## How to train

Two backends are available. The PyTorch path is the cross-platform
default; the PaddlePaddle path is the one that produced the held-out
metrics reported in the paper.

### PyTorch path (any GPU with CUDA + transformers)

```bash
python skills/cleantest-coverage-filter/scripts/prepare_data.py \
  --input_csv path/to/filter_train.csv \
  --output_dir path/to/splits

python skills/cleantest-coverage-filter/scripts/train_model.py \
  --base_model Qwen/Qwen2.5-Coder-0.5B \
  --train_csv path/to/splits/train.csv \
  --valid_csv path/to/splits/valid.csv \
  --output_model ./coverage_model_qwen \
  --epochs 2 --batch_size 8 --gradient_accumulation_steps 2 \
  --learning_rate 2e-5 --lr_scheduler_type cosine \
  --max_seq_length 384 --fp16
```

### PaddlePaddle path (Baidu AI Studio A800 80 GB)

```bash
bash skills/cleantest-coverage-filter/scripts_paddle/train_qwen_baidu.sh
```

Step-by-step instructions, including environment setup, data staging
and recovery from common failure modes, are in
`docs/training-on-baidu-aistudio.md`.

## How to evaluate (held-out)

```bash
python skills/cleantest-coverage-filter/scripts/evaluate_model.py \
  --input_csv path/to/splits/test.csv \
  --model_path ./coverage_model_qwen \
  --output_predictions path/to/splits/test_pred.csv \
  --threshold 0.01
```

The PaddlePaddle counterpart lives at
`skills/cleantest-coverage-filter/scripts_paddle/evaluate_model.py` and
takes the same arguments.

## How to Use for Inference

```bash
python skills/cleantest-coverage-filter/scripts/coverage_predictor.py \
  --input_csv path/to/data.csv \
  --output_csv filtered.csv \
  --model_path ./coverage_model_qwen \
  --threshold 0.01
```
