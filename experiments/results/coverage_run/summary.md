# Filter 3 Coverage Run on `filter_train.csv`

This directory archives **two** complementary experiments on
`filter_train.csv` from the LessIsMore-FSE2025 replication package:

1. **Label-mode threshold sensitivity sweep** -- pure $O(N)$ row scan
   over the JaCoCo `condition_cover_rate` ground-truth labels (no
   model, no GPU). Used to validate that the deterministic Filter 3
   path applies any user-supplied threshold correctly.
2. **Model-mode training and held-out evaluation** -- fine-tunes
   Qwen2.5-Coder-0.5B on a stratified 80/10/10 split of the same file
   on a single A800 80 GB and reports held-out regression /
   classification metrics. Replaces the CodeGPT recipe of the original
   CleanTest paper.

The two experiments use the exact same input file (`filter_train.csv`,
SHA-256 below); the model-mode experiment additionally uses the
80/10/10 split produced by `prepare_data.py` with seed 42.

---

## Input dataset (shared)

- File: `dataset/training_dataset/filter_dataset/filter_train.csv`
- Source: LessIsMore-FSE2025 replication package
  (Zenodo DOI 10.5281/zenodo.15347368)
- SHA-256: `8eaed383a582cfe43a545d8f8e95213734bb639b8b4fba3db17a63e9b02cf87f`
- Rows: **469,174** (already passed Filter 1 + Filter 2 in the
  original CleanTest pipeline)
- Columns: `idx, src_fm, target, condition_cover_rate, line_cover_rate`

### Coverage label statistics

| metric | value |
|---|---:|
| min    | 0.0110 |
| max    | 1.9100 |
| mean   | 0.1271 |
| median | 0.1080 |
| std    | 0.1007 |

Note: `min = 0.011 > 0.01` confirms that `filter_train.csv` is the
post-CleanTest output produced with the paper's default threshold of
0.01 -- every sample whose `condition_cover_rate < 0.01` had already
been removed.

---

## Experiment 1 -- Label-mode threshold sensitivity sweep

- **Date**: 2026-05-18
- **Hardware**: Apple M3, 16 GB RAM, macOS (arm64)
- **Software**: Python 3.9.6, pandas 2.3.3
- **Output**: `coverage_sweep.json` (machine-readable),
  `run_log.txt` (clean log).

| threshold | removed | removed % | kept | wall-clock (s) | throughput (samples/s) |
|---:|---:|---:|---:|---:|---:|
| 0.010 | 0       | 0.00 %  | 469,174 | 6.55 | 71,672 |
| 0.050 | 84,021  | 17.91 % | 385,153 | 6.43 | 72,932 |
| 0.100 | 212,059 | 45.20 % | 257,115 | 6.42 | 73,042 |
| 0.150 | 327,016 | 69.70 % | 142,158 | 6.41 | 73,224 |
| 0.200 | 400,999 | 85.47 % | 68,175  | 6.43 | 72,914 |
| 0.300 | 448,842 | 95.67 % | 20,332  | 6.49 | 72,306 |

### Reproduction (label mode)

```python
from cleantest_agent.pipeline import run_coverage_filter
from cleantest_agent.report_generator import NoiseReport
import pandas as pd
df = pd.read_csv('filter_train.csv', low_memory=False)
for t in [0.01, 0.05, 0.10, 0.15, 0.20, 0.30]:
    report = NoiseReport(total_samples=len(df))
    rm = run_coverage_filter(df, report, threshold=t)
    print(t, len(rm), len(rm) / len(df))
```

---

## Experiment 2 -- Model-mode training and held-out evaluation

- **Date**: 2026-05-24
- **Hardware**: NVIDIA A800-SXM4-80 GB (Compute Capability 8.0,
  79.3 GB HBM) on Baidu PaddlePaddle AI Studio
- **Software**: PaddlePaddle 3.0 + PaddleNLP 3.0.0b4
  (`aistudio_sdk` 0.2.5), Python 3.10.10, CUDA 12.6 runtime
  under driver 12.8, bf16 mixed precision
- **Base model**: Qwen/Qwen2.5-Coder-0.5B (494 M params, Alibaba
  Tongyi Lab, 2024)
- **End-to-end notebook**: [`../../main-final.ipynb`](../../main-final.ipynb)

### Training configuration

| Property | Value |
|---|---|
| Train / valid / test rows | 375,338 / 46,915 / 46,921 (stratified 80/10/10 by quintile of `condition_cover_rate`, seed 42) |
| Effective batch size | 64 (per-device 64, no gradient accumulation) |
| Max sequence length | 512 |
| Learning rate | 3e-5, cosine schedule, weight decay 0.01 |
| Mixed precision | bf16 |
| Epochs | 2 |
| Wall-clock | ~11,951 s (~3.32 h) |

### Validation metrics at end of training

| Metric | Value |
|---|---:|
| eval_loss (MSE) | 0.00365 |
| eval_mae        | 0.0304 |
| eval_rmse       | 0.0604 |
| eval_pearson_r  | 0.7927 |
| eval_spearman_ρ | 0.8477 |

(Source: `qwen_0p5b_a800/training_metrics.json`.)

### Held-out test metrics (46,921 samples)

#### Regression on continuous coverage

| Metric | Qwen2.5-Coder-0.5B (this work) | CodeGPT (Zhang et al., FSE 2025) |
|---|---:|---:|
| MAE  | **0.0309** | 0.0798 (~2.6× higher) |
| MSE  | **0.0039** | 0.0105 (~2.7× higher) |
| RMSE | **0.0628** | -- |
| R²   | **0.604**  | -- |
| Pearson r   | **0.778** | -- |
| Spearman ρ  | **0.848** | -- |

(Source: `test_metrics.json`. CodeGPT numbers are converted from the
original paper's percentage form: 7.98 % → 0.0798, 1.05 % → 0.0105.)

#### Threshold-aware low-coverage detection

`filter_train.csv` is the post-CleanTest output, so no held-out sample
satisfies `y_true < 0.01` and the original paper's default threshold is
degenerate on this data. The sweep below evaluates the model at
operationally meaningful thresholds:

| τ      | Pos. % | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|
| 0.010  | 0.0 %  | --     | --     | --     |
| 0.030  | 8.2 %  | 0.578 | 0.244 | 0.343 |
| 0.050  | 17.9 % | 0.776 | 0.607 | 0.681 |
| 0.075  | 31.2 % | 0.838 | 0.769 | 0.802 |
| **0.100** | **45.4 %** | **0.880** | **0.835** | **0.857** |
| 0.125  | 58.3 % | 0.905 | 0.869 | 0.887 |
| 0.150  | 69.6 % | 0.924 | 0.900 | 0.912 |
| 0.200  | 85.5 % | 0.950 | 0.948 | 0.949 |

(Source: `test_threshold_sweep.json`, computed from
`test_pred_a800.csv`.)

### Reproduction (model mode)

```bash
# 1. Stratified 80/10/10 split (deterministic given seed=42).
python skills/cleantest-coverage-filter/scripts_paddle/prepare_data.py \
    --input_csv data/filter_train.csv \
    --output_dir experiments/results/coverage_run/splits \
    --seed 42

# 2. Fine-tune on a single A800 80 GB.
python skills/cleantest-coverage-filter/scripts_paddle/train_model.py \
    --base_model Qwen/Qwen2.5-Coder-0.5B \
    --train_csv  experiments/results/coverage_run/splits/train.csv \
    --valid_csv  experiments/results/coverage_run/splits/valid.csv \
    --output_model experiments/results/coverage_run/qwen_0p5b_a800 \
    --epochs 2 --batch_size 64 --max_seq_length 512 \
    --learning_rate 3e-5 --bf16

# 3. Held-out evaluation.
python skills/cleantest-coverage-filter/scripts_paddle/evaluate_model.py \
    --input_csv  experiments/results/coverage_run/splits/test.csv \
    --model_path experiments/results/coverage_run/qwen_0p5b_a800 \
    --output_predictions experiments/results/coverage_run/test_pred_a800.csv \
    --threshold 0.01
```

The full step-by-step procedure (including AI-Studio-specific
environment workarounds) is in
[`../../../docs/training-on-baidu-aistudio.md`](../../../docs/training-on-baidu-aistudio.md);
the notebook variant is
[`../../main-final.ipynb`](../../main-final.ipynb).

---

## Files in this directory

### Label-mode experiment

- `coverage_sweep.json` -- machine-readable threshold sweep results
- `run_log.txt` -- clean run log (no progress-bar noise)

### Model-mode experiment

- `training_metrics.json` -- final training summary (config + validation
  metrics)
- `metrics.jsonl` -- per-step / per-eval / per-save JSONL stream emitted
  by `JsonlLogCallback` during training
- `test_metrics.json` -- held-out scalar metrics (regression + classification at τ = 0.01)
- `test_pred_a800.csv` -- held-out predictions (`src_fm, target, condition_cover_rate, pred_coverage`)
- `test_threshold_sweep.json` -- held-out classification metrics at
  τ ∈ {0.01, 0.03, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20}

### Shared

- `summary.md` -- this human-readable summary
