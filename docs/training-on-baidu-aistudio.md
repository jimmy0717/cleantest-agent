# Filter 3 Training on Baidu PaddlePaddle AI Studio

This document records the training procedure for the Filter 3 coverage
regression model (Qwen2.5-Coder-0.5B) on Baidu PaddlePaddle AI Studio.
The procedure described here is the one actually used to produce the
held-out metrics reported in `report/main.tex`,
Section 7.5 (`tab:filter3-model-mode`).

The end-to-end run is also packaged as `cleantest-agent/main.ipynb`,
which executes the same scripts cell by cell. This document is the
terminal-driven counterpart for users who prefer a shell session.

## Hardware and software

| Item | Value |
|---|---|
| GPU | NVIDIA A800 80 GB |
| Framework | PaddlePaddle 3.0 + PaddleNLP 3.0.0b3 |
| Python | 3.10 |
| Mixed precision | bf16 |
| Effective batch size | 32 (per-device 32, no gradient accumulation) |
| Max sequence length | 512 |
| Learning rate | 2e-5, cosine schedule |
| Epochs | 2 |

The PyTorch version of the same scripts (`scripts/train_qwen_baidu.sh`)
also runs on V100 32 GB with `fp16`, `BATCH_SIZE=8`, `GRAD_ACCUM=2`,
`MAX_LEN=384`. The PaddlePaddle scripts under `scripts_paddle/` are the
ones that produced the numbers in the report.

## Prerequisites

- An AI Studio notebook project with at least one A800 80 GB allocation.
- The `filter_train.csv` dataset mounted under `/home/aistudio/data/`
  (LessIsMore-FSE2025 replication package, 469,174 rows, ~850 MB).
- The repository archive `cleantest-agent-v3.zip` uploaded under
  `/home/aistudio/work/`.

## Steps

### 1. Allocate the instance

Stop the running instance, switch the runtime to A800 80 GB with
PaddlePaddle 3.0 + Python 3.10, and restart. The persistent directory
`/home/aistudio/work/` survives the switch; the model cache directory
`.ms_cache/` may or may not be preserved and is rebuilt below if absent.

### 2. Unpack the code

```bash
cd /home/aistudio/work
unzip -oq cleantest-agent-v3.zip
chmod +x cleantest-agent/skills/cleantest-coverage-filter/scripts_paddle/train_qwen_baidu.sh
```

### 3. Verify the environment

```python
import sys, paddle, paddlenlp
print(paddle.__version__, paddlenlp.__version__)
print(paddle.device.cuda.get_device_name(0))
print(paddle.device.cuda.get_device_properties(0).total_memory / 1024**3)

from paddlenlp.transformers import Qwen2ForSequenceClassification, AutoTokenizer
```

Expected: PaddlePaddle 3.0.x, PaddleNLP 3.0.0b3, device
`NVIDIA A800-SXM4-80GB`, total memory near 79 GB. The
`Qwen2ForSequenceClassification` import must succeed; otherwise the
PaddleNLP installation is incomplete and needs

```bash
pip install -U paddlenlp>=3.0.0b3 aistudio_sdk==0.2.5 \
    jieba seqeval datasets scipy>=1.10 scikit-learn>=1.3 \
    sentencepiece safetensors huggingface_hub>=0.20 modelscope>=1.30 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
```

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

### 6. Smoke run (10 % of training data)

```bash
cd /home/aistudio/work/cleantest-agent

SKIP_INSTALL=1 \
PRECISION=bf16 \
TRAIN_SUBSAMPLE=0.1 \
EPOCHS=1 \
BATCH_SIZE=32 \
GRAD_ACCUM=1 \
MAX_LEN=512 \
LR=2e-5 \
BASE_MODEL=/home/aistudio/work/cleantest-agent/.ms_cache/Qwen/Qwen2___5-Coder-0___5B \
MODEL_OUT=experiments/results/coverage_run/qwen_smoke_a800 \
LOG_FILE=experiments/results/coverage_run/smoke_a800.log \
bash skills/cleantest-coverage-filter/scripts_paddle/train_qwen_baidu.sh
```

Expected wall-clock: 8–10 minutes (1,173 optimisation steps plus one
evaluation pass over the 47 K validation set). The run is considered
healthy when the resulting `training_metrics.json` contains
`eval_mse < 0.05` and the training log shows monotonically decreasing
loss.

### 7. Full training

```bash
cd /home/aistudio/work/cleantest-agent

nohup env SKIP_INSTALL=1 \
    PRECISION=bf16 \
    EPOCHS=2 \
    BATCH_SIZE=32 \
    GRAD_ACCUM=1 \
    MAX_LEN=512 \
    LR=2e-5 \
    BASE_MODEL=/home/aistudio/work/cleantest-agent/.ms_cache/Qwen/Qwen2___5-Coder-0___5B \
    MODEL_OUT=experiments/results/coverage_run/qwen_0p5b_a800 \
    LOG_FILE=experiments/results/coverage_run/train_a800.log \
    bash skills/cleantest-coverage-filter/scripts_paddle/train_qwen_baidu.sh \
    > experiments/results/coverage_run/nohup_a800.out 2>&1 &

echo "$!" > experiments/results/coverage_run/train_a800.pid
```

Expected wall-clock: roughly three hours. The script checkpoints every
2,500 steps and evaluates on the validation set at the same cadence; an
early-stopping callback with patience 3 is registered, so the run may
finish before all 23,460 steps if validation MSE stops improving.

Progress can be monitored with:

```bash
PID=$(cat experiments/results/coverage_run/train_a800.pid)
ps -p "$PID" -o pid,etime,cmd
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
tail -n 20 experiments/results/coverage_run/train_a800.log
```

### 8. Held-out evaluation

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

### 9. Files to download

The minimum set of files needed locally for editing the report:

- `experiments/results/coverage_run/test_metrics.json`
- `experiments/results/coverage_run/qwen_0p5b_a800/training_metrics.json`
- `experiments/results/coverage_run/train_a800.log`

The trained checkpoint itself (about 1 GB) does not need to be
downloaded for grading; the evaluation script writes all reportable
numbers into `test_metrics.json`.

## Known issues and fixes

| Symptom | Resolution |
|---|---|
| `Cannot import torch ... system compatibility` | The PaddlePaddle image blocks `torch`. The `scripts_paddle/` variant has no PyTorch dependency. |
| `safetensors metadata error` when loading the base model | The Qwen2.5 weights are stored in PyTorch format. The training script passes `convert_from_torch=True` to `Qwen2ForSequenceClassification.from_pretrained`. |
| `condition_cover_rate range outside [0, 1]` warning | 305 rows in `filter_train.csv` have labels above 1.0. The training script clips them at runtime; no manual preprocessing is needed. |
| Training loss stuck near 5.0 | An older draft of the script omitted the sigmoid wrapper around the regression head. The current `train_model.py` wraps the forward pass with sigmoid + MSE so that the output stays in [0, 1]. |
| `Repo id must be in form ...` from `snapshot_download` | The script branches on `[[ -d $BASE_MODEL ]]` and skips the download when a local directory is supplied. |
| `_bounded_forward() got multiple values for argument 'input_ids'` | The PaddleNLP `wrap_fwd` decorator calls the forward as `value(self, *args, **kwargs)`. The wrapper signature must explicitly receive `self`. The current script uses `def _bounded_forward(self, *fwd_args, **fwd_kwargs)`. |

## Reproducibility

All randomness is seeded via `--seed 42` (default). The 80/10/10 split
is a stratified split by quintile of `condition_cover_rate`, so
re-running `prepare_data.py` on the same input CSV produces identical
splits across hardware. The training script writes a JSON record of the
exact arguments used, so the metrics file plus the log alone are
sufficient to reconstruct the configuration of any run.
