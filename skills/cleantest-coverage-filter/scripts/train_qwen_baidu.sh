#!/usr/bin/env bash
# ----------------------------------------------------------------------
# Filter 3 model-mode training launcher for Baidu PaddlePaddle AI Studio
# (V100 32 GB, single-GPU notebook environment).
#
# What this script does, in order:
#   1) sanity-checks the Python and CUDA environment;
#   2) installs the required Python packages (PyTorch + transformers
#      + datasets + scipy) into the active interpreter;
#   3) downloads the Qwen2.5-Coder-0.5B base weights to a local cache;
#   4) prepares an 80/10/10 stratified split of the LessIsMore-FSE2025
#      filter_train.csv;
#   5) launches train_model.py with V100-tuned hyperparameters;
#   6) writes a wall-clock log next to the produced checkpoint.
#
# Edit the four ROOT/INPUT/OUTPUT/HF_CACHE variables in the
# CONFIGURATION section below before running.  Everything else is
# meant to be left untouched.
# ----------------------------------------------------------------------

set -euo pipefail

# ============================== CONFIG ================================
# Repository root checked out on AI Studio (e.g. /home/aistudio/work/cleantest-agent)
ROOT="${ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
# Path to filter_train.csv from the LessIsMore-FSE2025 replication package
INPUT_CSV="${INPUT_CSV:-${ROOT}/data/filter_train.csv}"
# Where to write split CSVs and the trained checkpoint
SPLIT_DIR="${SPLIT_DIR:-${ROOT}/experiments/results/coverage_run/splits}"
MODEL_OUT="${MODEL_OUT:-${ROOT}/experiments/results/coverage_run/qwen_0p5b_v1}"
LOG_FILE="${LOG_FILE:-${ROOT}/experiments/results/coverage_run/train.log}"
# HuggingFace download cache (AI Studio sometimes needs a writable path)
HF_CACHE="${HF_CACHE:-${ROOT}/.hf_cache}"
# Base model
BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-Coder-0.5B}"
# Training hyperparameters (V100 32 GB tuned, speed-optimized)
EPOCHS="${EPOCHS:-2}"
BATCH_SIZE="${BATCH_SIZE:-8}"
GRAD_ACCUM="${GRAD_ACCUM:-2}"
MAX_LEN="${MAX_LEN:-384}"
LR="${LR:-2e-5}"
LR_SCHED="${LR_SCHED:-cosine}"
NUM_WORKERS="${NUM_WORKERS:-4}"
# Fraction of training rows to use; set to e.g. 0.1 for a fast smoke
# run (~20 minutes), 1.0 for the final reported run.
TRAIN_SUBSAMPLE="${TRAIN_SUBSAMPLE:-1.0}"
SEED="${SEED:-42}"
# ======================================================================

mkdir -p "${SPLIT_DIR}" "${MODEL_OUT}" "$(dirname "${LOG_FILE}")" "${HF_CACHE}"

export HF_HOME="${HF_CACHE}"
export TRANSFORMERS_CACHE="${HF_CACHE}"
export TOKENIZERS_PARALLELISM=false
# Mirror through Hugging Face's mainland-China-friendly endpoint when
# the default huggingface.co is unreachable from inside AI Studio.
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

echo "============================================================"
echo "[1/5] Environment summary"
echo "============================================================"
python -V
python - <<'PY'
import torch, sys
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device:", torch.cuda.get_device_name(0))
    print("memory:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1), "GB")
else:
    print("WARNING: no GPU detected; training will not be feasible.", file=sys.stderr)
PY

echo
echo "============================================================"
echo "[2/5] Install required Python packages"
echo "============================================================"
if [[ "${SKIP_INSTALL:-0}" == "1" ]]; then
    echo "SKIP_INSTALL=1 -> skipping pip install (assuming the active"
    echo "environment already has torch / transformers / datasets etc.)."
else
    pip install --upgrade pip
    pip install -e "${ROOT}[coverage]"
    pip install "datasets>=2.14" "scipy>=1.10" "scikit-learn>=1.3"
fi

echo
echo "============================================================"
echo "[3/5] Pre-fetch base model weights to local cache"
echo "============================================================"
python - <<PY
from huggingface_hub import snapshot_download
import os
snapshot_download(
    repo_id="${BASE_MODEL}",
    cache_dir=os.environ.get("HF_HOME", None),
    local_files_only=False,
    resume_download=True,
)
print("OK")
PY

echo
echo "============================================================"
echo "[4/5] Prepare stratified train / valid / test split"
echo "============================================================"
python "${ROOT}/skills/cleantest-coverage-filter/scripts/prepare_data.py" \
    --input_csv "${INPUT_CSV}" \
    --output_dir "${SPLIT_DIR}" \
    --train_ratio 0.8 \
    --valid_ratio 0.1 \
    --seed "${SEED}"

echo
echo "============================================================"
echo "[5/5] Launch training (${BASE_MODEL})"
echo "============================================================"
START_TS=$(date +%s)
python -u "${ROOT}/skills/cleantest-coverage-filter/scripts/train_model.py" \
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
    --fp16 2>&1 | tee "${LOG_FILE}"
END_TS=$(date +%s)

echo
echo "============================================================"
echo "Training complete."
echo "  Wall-clock seconds: $((END_TS - START_TS))"
echo "  Checkpoint: ${MODEL_OUT}"
echo "  Log: ${LOG_FILE}"
echo "  Validation metrics: ${MODEL_OUT}/training_metrics.json"
echo "============================================================"

echo
echo "Next: run held-out test evaluation"
echo "  python ${ROOT}/skills/cleantest-coverage-filter/scripts/coverage_predictor.py \\"
echo "      --input_csv  ${SPLIT_DIR}/test.csv \\"
echo "      --output_csv ${SPLIT_DIR}/test_pred.csv \\"
echo "      --model_path ${MODEL_OUT} \\"
echo "      --threshold 0.01"
