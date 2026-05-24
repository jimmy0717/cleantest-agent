#!/usr/bin/env bash
# ----------------------------------------------------------------------
# Filter 3 model-mode training launcher (PaddlePaddle version).
# Defaults match the configuration that produced the held-out numbers
# in report/main.tex Section 7.5 (A800 80 GB, bf16, batch 64,
# max_seq 512, lr 3e-5 cosine, 2 epochs, ~3.32 h wall-clock).
# Override the env vars below to run on smaller GPUs.
#
# Usage:
#   # A800 80 GB (default; the configuration used for the paper's numbers):
#   bash scripts_paddle/train_qwen_baidu.sh
#
#   # Smaller GPU without bf16 support: switch to fp16 + smaller batch
#   # but keep the effective batch size (BATCH_SIZE * GRAD_ACCUM) at 64:
#   PRECISION=fp16 BATCH_SIZE=8 GRAD_ACCUM=8 MAX_LEN=512 \
#   bash scripts_paddle/train_qwen_baidu.sh
# ----------------------------------------------------------------------

set -euo pipefail

# ============================== CONFIG ================================
ROOT="${ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
INPUT_CSV="${INPUT_CSV:-${ROOT}/data/filter_train.csv}"
SPLIT_DIR="${SPLIT_DIR:-${ROOT}/experiments/results/coverage_run/splits}"
MODEL_OUT="${MODEL_OUT:-${ROOT}/experiments/results/coverage_run/qwen_0p5b_paddle}"
LOG_FILE="${LOG_FILE:-${ROOT}/experiments/results/coverage_run/train_paddle.log}"
HF_CACHE="${HF_CACHE:-${ROOT}/.hf_cache}"
BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-Coder-0.5B}"

# A800-tuned defaults (override via env for smaller GPUs):
PRECISION="${PRECISION:-bf16}"     # bf16 (A800/A100/H100) or fp16 (older Ampere/Volta)
EPOCHS="${EPOCHS:-2}"
BATCH_SIZE="${BATCH_SIZE:-64}"     # A800 80 GB headroom; lower this on smaller GPUs
GRAD_ACCUM="${GRAD_ACCUM:-1}"      # A800 needs no accumulation; raise to keep effective bs at 64
MAX_LEN="${MAX_LEN:-512}"
LR="${LR:-3e-5}"
LR_SCHED="${LR_SCHED:-cosine}"
NUM_WORKERS="${NUM_WORKERS:-4}"
TRAIN_SUBSAMPLE="${TRAIN_SUBSAMPLE:-1.0}"
SEED="${SEED:-42}"
# ======================================================================

mkdir -p "${SPLIT_DIR}" "${MODEL_OUT}" "$(dirname "${LOG_FILE}")" "${HF_CACHE}"

export HF_HOME="${HF_CACHE}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export TOKENIZERS_PARALLELISM=false

case "${PRECISION}" in
    bf16)  PRECISION_FLAG="--bf16" ;;
    fp16)  PRECISION_FLAG="--fp16" ;;
    fp32)  PRECISION_FLAG="" ;;
    *)     echo "ERROR: unknown PRECISION=${PRECISION} (use bf16/fp16/fp32)" >&2
           exit 2 ;;
esac

echo "============================================================"
echo "[1/5] Environment summary"
echo "============================================================"
python -V
python - <<'PYENV'
import paddle, sys
print("paddle:", paddle.__version__)
print("cuda compiled:", paddle.device.is_compiled_with_cuda())
if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
    print("device:", paddle.device.cuda.get_device_name(0))
    props = paddle.device.cuda.get_device_properties(0)
    print("memory:", round(props.total_memory / 1024**3, 1), "GB")
    name = paddle.device.cuda.get_device_name(0).lower()
    if "a800" in name or "a100" in name or "h100" in name or "h800" in name:
        print("supports_bf16: True (Ampere/Hopper)")
    else:
        print("supports_bf16: False (use fp16 instead)")
else:
    print("WARNING: no GPU detected.", file=sys.stderr)
PYENV

echo
echo "============================================================"
echo "[2/5] Install required Python packages"
echo "============================================================"
if [[ "${SKIP_INSTALL:-0}" == "1" ]]; then
    echo "SKIP_INSTALL=1 -> skipping pip install."
else
    pip install --upgrade pip
    pip install -U "paddlenlp>=3.0.0b0" "scipy>=1.10" "scikit-learn>=1.3" \
        "huggingface_hub>=0.20" "pandas>=1.5" "modelscope>=1.30" \
        -i https://pypi.tuna.tsinghua.edu.cn/simple
fi

echo
echo "============================================================"
echo "[3/5] Pre-fetch base model weights"
echo "============================================================"
if [[ -d "${BASE_MODEL}" ]]; then
    echo "BASE_MODEL is a local directory; skipping download."
    echo "  -> ${BASE_MODEL}"
else
    # Prefer ModelScope (in-China stable); fall back to hf-mirror.
    python - <<'PYDOWN'
import os, sys
repo = os.environ["BASE_MODEL"]
ms_dir = os.environ.get("HF_HOME") + "/modelscope"
try:
    from modelscope import snapshot_download as ms_download
    print("Downloading via ModelScope:", repo)
    p = ms_download(repo, cache_dir=ms_dir)
    print("OK ->", p)
    # Expose for downstream stages
    print(f"::resolved_local_path={p}")
except Exception as e:
    print("ModelScope failed:", e, "  -> fallback to hf-mirror.com", file=sys.stderr)
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=repo, cache_dir=os.environ.get("HF_HOME"),
                      resume_download=True)
    print("OK (hf-mirror)")
PYDOWN
fi

echo
echo "============================================================"
echo "[4/5] Prepare stratified train/valid/test split"
echo "============================================================"
python "${ROOT}/skills/cleantest-coverage-filter/scripts_paddle/prepare_data.py" \
    --input_csv "${INPUT_CSV}" \
    --output_dir "${SPLIT_DIR}" \
    --train_ratio 0.8 \
    --valid_ratio 0.1 \
    --seed "${SEED}"

echo
echo "============================================================"
echo "[5/5] Launch training (${BASE_MODEL}, ${PRECISION})"
echo "============================================================"
START_TS=$(date +%s)
python -u "${ROOT}/skills/cleantest-coverage-filter/scripts_paddle/train_model.py" \
    --base_model "${BASE_MODEL}" \
    --train_csv "${SPLIT_DIR}/train.csv" \
    --valid_csv "${SPLIT_DIR}/valid.csv" \
    --output_model "${MODEL_OUT}" \
    --epochs "${EPOCHS}" \
    --batch_size "${BATCH_SIZE}" \
    --gradient_accumulation_steps "${GRAD_ACCUM}" \
    --max_seq_length "${MAX_LEN}" \
    --learning_rate "${LR}" \
    --lr_scheduler_type "${LR_SCHED}" \
    --dataloader_num_workers "${NUM_WORKERS}" \
    --train_subsample "${TRAIN_SUBSAMPLE}" \
    --seed "${SEED}" \
    ${PRECISION_FLAG} 2>&1 | tee "${LOG_FILE}"
END_TS=$(date +%s)

echo
echo "============================================================"
echo "Training complete."
echo "  Wall-clock seconds: $((END_TS - START_TS))"
echo "  Checkpoint: ${MODEL_OUT}"
echo "  Log: ${LOG_FILE}"
echo "============================================================"
