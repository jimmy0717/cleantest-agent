# Model Card: Filter 3 Coverage Regression (Qwen2.5-Coder-0.5B)

> This card describes the base model and training recipe used for the
> model-mode code path of the `cleantest-coverage-filter` skill. **All
> held-out numbers in this card and in `report/main.tex` Section 7.5
> were produced on a single NVIDIA A800 80 GB on Baidu PaddlePaddle
> AI Studio with bf16, batch 64, max_seq 512, and lr 3e-5 cosine for
> 2 epochs (~3.32 h wall-clock).**
>
> The training and evaluation code is provided in two backends, both
> of which produce the same model architecture (Qwen2 +
> SequenceClassification head):
>
> - `scripts_paddle/` -- PaddlePaddle 3.0 + PaddleNLP 3.0.0b4
>   (Python 3.10.10, CUDA 12.6 runtime), run on A800-SXM4-80 GB.
>   **This is the variant that produced the held-out
>   metrics reported below and in Section 7.5 of the paper.**
> - `scripts/` -- PyTorch + HuggingFace Transformers, provided as a
>   cross-platform alternative for users without access to A800.
>   This path has not been used to produce the numbers in this report,
>   but is functionally equivalent and follows the same recipe at a
>   smaller per-device batch size when memory is tighter.
>
> Held-out test metrics are recorded in
> `experiments/results/coverage_run/test_metrics.json` (regression)
> and `test_threshold_sweep.json` (classification at multiple
> thresholds). When neither these files nor a usable trained
> checkpoint are available, the skill falls back to label mode,
> which performs an $O(N)$ row scan over the JaCoCo ground-truth
> labels. All Filter 3 numbers in Section 7.4 of the paper come
> from label mode; Section 7.5 is what the model mode produced.

## Base model and training recipe

All values below describe the actual training run on A800 80 GB that
produced the held-out numbers in the next section.

| Property | Value |
|----------|-------|
| Base model | `Qwen/Qwen2.5-Coder-0.5B` (Alibaba Tongyi Lab, 2024) |
| Parameters | ~494 M |
| Architecture | Qwen2 decoder-only causal LM, used via `Qwen2ForSequenceClassification` with `num_labels=1` for regression |
| Code-specific pre-training | Yes (Qwen2.5-Coder series) |
| Task | Predict branch coverage (`condition_cover_rate` from JaCoCo) of a unit test given focal method + test code |
| Output | A single float in [0, 1] (sigmoid-wrapped) |
| Training data | LessIsMore-FSE2025 `filter_train.csv` (469,174 rows), stratified 80/10/10 split by coverage quintile, seed 42 |
| Train / valid / test rows | 375,338 / 46,915 / 46,921 |
| Hardware | Single NVIDIA A800-SXM4-80 GB (Compute Capability 8.0, 79.3 GB HBM) on Baidu PaddlePaddle AI Studio |
| Framework | PaddlePaddle 3.0 + PaddleNLP 3.0.0b4 (`aistudio_sdk` 0.2.5) |
| Runtime | Python 3.10.10, CUDA 12.6 runtime under driver 12.8 |
| Mixed precision | bf16 (natively supported on A800) |
| Effective batch size | 64 (per-device 64, no gradient accumulation) |
| Max sequence length | 512 tokens |
| Optimiser | AdamW, lr 3e-5 cosine, weight decay 0.01, linear warmup |
| Epochs | 2 |
| Wall-clock training time | ~11,951 s (~3.32 h) |
| Validation MSE at end of training | 0.00365 (Pearson r 0.793, Spearman ρ 0.848) |
| Original paper baseline | CodeGPT, MAE 7.98 %, MSE 1.05 % (Zhang et al., FSE 2025) |

The forward pass is wrapped to apply a sigmoid before the MSE loss so
that the regression output stays inside the same [0, 1] range as the
training labels. This is also the value that the inference script
returns, so no post-hoc scaling is needed at evaluation time.

### Portability note (PyTorch path on smaller GPUs)

The PyTorch + Transformers variant under `scripts/` runs the same
recipe on smaller GPUs by lowering the per-device batch size and
using `fp16` instead of `bf16`. We have not produced held-out numbers
on this configuration ourselves; users who reproduce on a smaller
GPU should expect the per-step throughput to drop linearly with
per-device batch size, but the final regression quality to be
comparable provided the *effective* batch size (per-device × gradient
accumulation) and learning rate are kept identical.

## Held-out test metrics

Reported on the 10 % held-out test split (46,921 samples). All numbers
are extracted from `experiments/results/coverage_run/test_metrics.json`
and `test_threshold_sweep.json`.

### Regression on continuous coverage

| Metric | Value | CodeGPT baseline (Zhang et al., FSE 2025) | Improvement |
|---|---:|---:|---|
| MAE  | **0.0309** | 0.0798 | ~2.6× lower |
| MSE  | **0.0039** | 0.0105 | ~2.7× lower |
| RMSE | **0.0628** | -- | -- |
| R²   | **0.604**  | -- | -- |
| Pearson r | **0.778** | -- | -- |
| Spearman ρ | **0.848** | -- | -- |

CodeGPT numbers are converted from the paper's percentage form (7.98 %
→ 0.0798, 1.05 % → 0.0105) for direct comparison on the [0, 1] scale.

### Threshold-aware low-coverage detection

`filter_train.csv` is the post-CleanTest output, so no held-out sample
satisfies `y_true < 0.01` and the original paper's default threshold
becomes degenerate on this data. The sweep below shows performance at
operationally meaningful thresholds:

| τ      | Pos. % | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|
| 0.010  | 0.0 %  | -- | -- | -- |
| 0.030  | 8.2 %  | 0.578 | 0.244 | 0.343 |
| 0.050  | 17.9 % | 0.776 | 0.607 | 0.681 |
| 0.075  | 31.2 % | 0.838 | 0.769 | 0.802 |
| **0.100** | **45.4 %** | **0.880** | **0.835** | **0.857** |
| 0.125  | 58.3 % | 0.905 | 0.869 | 0.887 |
| 0.150  | 69.6 % | 0.924 | 0.900 | 0.912 |
| 0.200  | 85.5 % | 0.950 | 0.948 | 0.949 |

## Why Qwen2.5-Coder-0.5B (and not GPT-2 / a 7B+ model)

The original CleanTest paper used **CodeGPT**, a continued-pretrained
GPT-2 (117M) on code. CodeGPT itself is no longer maintained on the
HuggingFace Hub at a stable identifier. We replace it with a stronger
modern open-weights small code model:

* **Qwen2.5-Coder-0.5B** (2024, Alibaba Tongyi Lab): code-specific
  pre-training on a large recent corpus, SOTA among open-weights
  small code models on HumanEval-Java / MBPP-Java; 500M parameters
  fit comfortably into a single A800 80 GB allocation for full
  fine-tuning at batch 64 / max_seq 512 in bf16, with no need for
  LoRA (which is unstable for a single-scalar regression head).

We deliberately avoid 7B+ backbones (DeepSeek-Coder-6.7B,
CodeFuse-13B, Qwen2.5-Coder-14B, etc.) because:

1. Branch coverage is a low-dimensional regression target; 7B+
   capacity is unnecessary and risks over-fitting on 469K rows.
2. 7B+ models on the same single-GPU allocation would either run
   out of memory at full fine-tuning or force LoRA training
   (training only ~1% of parameters), which is empirically unstable
   for a single-scalar regression head.
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
  --learning_rate 3e-5 --lr_scheduler_type cosine \
  --max_seq_length 512 --fp16
```

### PaddlePaddle path (Baidu AI Studio A800 80 GB)

The exact configuration that produced the held-out numbers above:

```bash
python skills/cleantest-coverage-filter/scripts_paddle/train_model.py \
  --base_model Qwen/Qwen2.5-Coder-0.5B \
  --train_csv path/to/splits/train.csv \
  --valid_csv path/to/splits/valid.csv \
  --output_model ./coverage_model_qwen \
  --epochs 2 --batch_size 64 \
  --learning_rate 3e-5 --lr_scheduler_type cosine \
  --max_seq_length 512 --bf16
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
