# Filter 3 Training on Baidu PaddlePaddle AI Studio

This document records the training procedure for the Filter 3 coverage
regression model (Qwen2.5-Coder-0.5B) on Baidu PaddlePaddle AI Studio.
The procedure described here is the one actually used to produce the
held-out metrics reported in `report/main.tex`,
Section 7.5 (`tab:filter3-model-mode`, `tab:filter3-classif-sweep`).

The end-to-end run is also packaged as
[`experiments/main-final.ipynb`](../experiments/main-final.ipynb), which
executes the same scripts cell by cell. This document is the
terminal-driven counterpart for users who prefer a shell session.

## Hardware and software

| Item | Value (used to produce the held-out numbers) |
|---|---|
| GPU | NVIDIA A800-SXM4-80 GB (Compute Capability 8.0, 79.3 GB HBM) |
| Platform | Baidu PaddlePaddle AI Studio |
| Framework | PaddlePaddle 3.0 + PaddleNLP 3.0.0b4 (`aistudio_sdk` 0.2.5) |
| Python | 3.10.10 |
| CUDA | 12.6 runtime under driver 12.8 |
| Mixed precision | bf16 (natively supported on A800) |
| Effective batch size | 64 (per-device 64, no gradient accumulation) |
| Max sequence length | 512 |
| Learning rate | 3e-5, cosine schedule |
| Weight decay | 0.01 |
| Epochs | 2 |
| Wall-clock | ~11,951 s (~3.32 h) |
| Held-out test MAE / RMSE / Pearson r | 0.0309 / 0.0628 / 0.778 |

The PyTorch version of the same scripts
(`skills/cleantest-coverage-filter/scripts/`, with the
`train_qwen_baidu.sh` launcher) is provided as a portable alternative
for users who want to reproduce the recipe on smaller GPUs; it has
not been used to produce any numbers in this report. The
PaddlePaddle scripts under `scripts_paddle/` are the ones that
produced the held-out numbers reported in the paper.

## Prerequisites

- An AI Studio notebook project with at least one A800 80 GB allocation.
- The `filter_train.csv` dataset mounted under `/home/aistudio/data/`
  (LessIsMore-FSE2025 replication package, 469,174 rows, ~850 MB).
- The repository archive `cleantest-agent-vN.zip` uploaded under
  `/home/aistudio/work/` (any recent revision works; the scripts under
  `skills/cleantest-coverage-filter/scripts_paddle/` are the only ones
  this guide needs).

## Steps

### 1. Allocate the instance

Stop the running instance, switch the runtime to A800 80 GB with
PaddlePaddle 3.0 + Python 3.10, and restart. The persistent directory
`/home/aistudio/work/` survives the switch; the model cache directory
`.ms_cache/` may or may not be preserved and is rebuilt below if absent.

### 2. Unpack the code

```bash
cd /home/aistudio/work
unzip -oq cleantest-agent-v*.zip
```

### 3. Verify the environment

```python
import sys, paddle, paddlenlp
print(paddle.__version__, paddlenlp.__version__)
print(paddle.device.cuda.get_device_name(0))
print(paddle.device.cuda.get_device_properties(0).total_memory / 1024**3)

from paddlenlp.transformers import Qwen2ForSequenceClassification, AutoTokenizer
```

Expected: PaddlePaddle 3.0.x, PaddleNLP 3.0.0b4 (b3 also works at the
same API), device `NVIDIA A800-SXM4-80GB`, total memory near 79 GB. The
`Qwen2ForSequenceClassification` import must succeed; otherwise the
PaddleNLP installation is incomplete and needs

```bash
# Install paddlenlp first, then pin aistudio_sdk back to 0.2.5
# (PaddleNLP 3.0.0b3/b4 will silently upgrade aistudio_sdk and break
# the import path unless the order is `paddlenlp` before
# `aistudio_sdk==0.2.5`).
pip install -U "paddlenlp>=3.0.0b3" \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -U aistudio_sdk==0.2.5 \
    "numpy>=1.26,<2.0" "scipy>=1.10,<1.13" \
    jieba seqeval datasets scikit-learn>=1.3 \
    sentencepiece safetensors huggingface_hub>=0.20 modelscope>=1.30 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
```

If `import paddlenlp` still fails with
`ImportError: cannot import name 'download' from 'aistudio_sdk.hub'`, see
the in-notebook patch in `experiments/main-final.ipynb` Cell 5
(`_patch_aistudio_hub_download`), which monkey-patches the missing
attribute without further pip churn.

### 4. Stage the dataset

```bash
mkdir -p /home/aistudio/work/cleantest-agent/data
SRC=$(find /home/aistudio/data -name "filter_train.csv" | head -1)
ln -sf "$SRC" /home/aistudio/work/cleantest-agent/data/filter_train.csv
```

The training script handles the 305 rows whose `condition_cover_rate`
is `> 1.0` by clipping at runtime; no preprocessing of the CSV is
required.

### 5. Stage the base model

```bash
WEIGHT_DIR=/home/aistudio/work/cleantest-agent/.ms_cache/Qwen/Qwen2___5-Coder-0___5B
if [ ! -f "$WEIGHT_DIR/model.safetensors" ]; then
    pip install -q modelscope
    python -c "from modelscope import snapshot_download; \
        snapshot_download('Qwen/Qwen2.5-Coder-0.5B', \
        cache_dir='/home/aistudio/work/cleantest-agent/.ms_cache')"
fi
ls -lh "$WEIGHT_DIR/model.safetensors"
```

Expected file size around 942 MB. ModelScope is preferred over
`huggingface.co` because direct access to the latter is unreliable from
the AI Studio network; `hf-mirror` works as a fallback.

### 6. Stratified split (once per dataset)

```bash
cd /home/aistudio/work/cleantest-agent

python skills/cleantest-coverage-filter/scripts_paddle/prepare_data.py \
    --input_csv data/filter_train.csv \
    --output_dir experiments/results/coverage_run/splits \
    --seed 42
```

Resulting split sizes: 375,338 train / 46,915 valid / 46,921 test.

### 7. Smoke run (10 % of training data)

```bash
cd /home/aistudio/work/cleantest-agent

python skills/cleantest-coverage-filter/scripts_paddle/train_model.py \
    --base_model /home/aistudio/work/cleantest-agent/.ms_cache/Qwen/Qwen2___5-Coder-0___5B \
    --train_csv  experiments/results/coverage_run/splits/train.csv \
    --valid_csv  experiments/results/coverage_run/splits/valid.csv \
    --output_model experiments/results/coverage_run/qwen_smoke_a800 \
    --epochs 1 --batch_size 64 --max_seq_length 512 \
    --learning_rate 3e-5 --bf16 \
    --train_subsample 0.1
```

Expected wall-clock on A800 80 GB: 8–10 minutes (~1,170 optimisation
steps plus one evaluation pass over the 47 K validation set). The run is
considered healthy when the resulting `training_metrics.json` contains
`eval_mse < 0.05` and the training log shows monotonically decreasing
loss.

### 8. Full training

```bash
cd /home/aistudio/work/cleantest-agent

# Run in the background so the SSH/notebook session can disconnect.
nohup python skills/cleantest-coverage-filter/scripts_paddle/train_model.py \
    --base_model /home/aistudio/work/cleantest-agent/.ms_cache/Qwen/Qwen2___5-Coder-0___5B \
    --train_csv  experiments/results/coverage_run/splits/train.csv \
    --valid_csv  experiments/results/coverage_run/splits/valid.csv \
    --output_model experiments/results/coverage_run/qwen_0p5b_a800 \
    --epochs 2 --batch_size 64 --max_seq_length 512 \
    --learning_rate 3e-5 --bf16 \
    > experiments/results/coverage_run/train_a800.log 2>&1 &

echo "$!" > experiments/results/coverage_run/train_a800.pid
```

Expected wall-clock: **~3.32 hours** (~11,951 s; ~11,730 optimisation
steps with batch 64 over the 375 K train rows × 2 epochs). A
`JsonlLogCallback` writes one line per logging / eval / save step into
`metrics.jsonl` inside the output directory, which the notebook's
real-time progress panel reads.

Progress can be monitored with:

```bash
PID=$(cat experiments/results/coverage_run/train_a800.pid)
ps -p "$PID" -o pid,etime,cmd
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
tail -n 20 experiments/results/coverage_run/train_a800.log
tail -n 5  experiments/results/coverage_run/qwen_0p5b_a800/metrics.jsonl
```

### 9. Held-out evaluation

```bash
cd /home/aistudio/work/cleantest-agent

python skills/cleantest-coverage-filter/scripts_paddle/evaluate_model.py \
    --input_csv  experiments/results/coverage_run/splits/test.csv \
    --model_path experiments/results/coverage_run/qwen_0p5b_a800 \
    --output_predictions experiments/results/coverage_run/test_pred_a800.csv \
    --batch_size 64 \
    --max_seq_length 512 \
    --threshold 0.01

cat experiments/results/coverage_run/test_metrics.json
```

The resulting JSON contains the nine fields used in
`report/main.tex` Table `tab:filter3-model-mode`:
`mae`, `mse`, `rmse`, `r2`, `pearson_r`, `spearman_rho`,
`precision`, `recall`, `f1`, plus the confusion-matrix counts
`tp`, `fp`, `fn`, `tn`.

For the threshold-aware F1 sweep at multiple operationally meaningful
thresholds (Table `tab:filter3-classif-sweep` in the paper), see
`experiments/main-final.ipynb` Cell 21, which post-processes
`test_pred_a800.csv` into `test_threshold_sweep.json`.

### 10. Files to download

The minimum set of files needed locally for editing the report:

- `experiments/results/coverage_run/test_metrics.json`
- `experiments/results/coverage_run/test_threshold_sweep.json`
- `experiments/results/coverage_run/test_pred_a800.csv`
- `experiments/results/coverage_run/qwen_0p5b_a800/training_metrics.json`
- `experiments/results/coverage_run/qwen_0p5b_a800/metrics.jsonl`
- `experiments/results/coverage_run/train_a800.log`

The trained checkpoint itself (about 1 GB) does not need to be
downloaded for grading; the evaluation script writes all reportable
numbers into `test_metrics.json` and `test_pred_a800.csv`.

## Known issues and fixes

| Symptom | Resolution |
|---|---|
| `Cannot import torch ... system compatibility` | The PaddlePaddle image blocks `torch`. The `scripts_paddle/` variant has no PyTorch dependency. |
| `safetensors metadata error` when loading the base model | The Qwen2.5 weights are stored in PyTorch format. The training script passes `convert_from_torch=True` to `Qwen2ForSequenceClassification.from_pretrained`. |
| `condition_cover_rate range outside [0, 1]` warning | 305 rows in `filter_train.csv` have labels above 1.0. The training script clips them at runtime; no manual preprocessing is needed. |
| Training loss stuck near 5.0 | An older draft of the script omitted the sigmoid wrapper around the regression head. The current `train_model.py` wraps the forward pass with sigmoid + MSE so that the output stays in [0, 1]. |
| `Repo id must be in form ...` from `snapshot_download` | The script branches on `[[ -d $BASE_MODEL ]]` and skips the download when a local directory is supplied. |
| `_bounded_forward() got multiple values for argument 'input_ids'` | The PaddleNLP `wrap_fwd` decorator calls the forward as `value(self, *args, **kwargs)`. The wrapper signature must explicitly receive `self`. The current script uses `def _bounded_forward(self, *fwd_args, **fwd_kwargs)`. |
| `ImportError: cannot import name 'download' from 'aistudio_sdk.hub'` | PaddleNLP 3.0.0b3/b4 expects an older `aistudio_sdk` API; new versions removed `hub.download`. Either install `aistudio_sdk==0.2.5` strictly *after* `paddlenlp`, or apply the in-notebook monkey-patch `_patch_aistudio_hub_download` from `experiments/main-final.ipynb` Cell 5. |

## Reproducibility

All randomness is seeded via `--seed 42` (default). The 80/10/10 split
is a stratified split by quintile of `condition_cover_rate`, so
re-running `prepare_data.py` on the same input CSV produces identical
splits across hardware. The training script writes a JSON record of the
exact arguments used into `training_metrics.json`, so the metrics file
plus the log alone are sufficient to reconstruct the configuration of
any run.
