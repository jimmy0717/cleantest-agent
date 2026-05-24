# CleanTest-Agent Experiment Results Summary

**Date**: 2026-05-18
**LLM Backend**: DeepSeek-V4-Flash (via Tencent Cloud TokenHub)
**Dataset**: Methods2Test (stratified sample of 500 rows from 5,000)
**Seed**: 42 (reproducible)

---

## Dataset Statistics

| Metric | Value |
|--------|-------|
| Sample Size | 500 |
| Noise Ratio | 46.2% (231 noisy, 269 clean) |

---

## RQ2: Model-Driven vs. Pure LLM

| Method | Precision | Recall | F1 | Accuracy | Time (s) | ms/sample |
|--------|-----------|--------|------|----------|-----------|-----------|
| Rule-based (ours) | 1.000 | 1.000 | 1.000 | 1.000 | 0.11 | 0.2 |
| LLM zero-shot | 0.505 | 0.221 | 0.307 | 0.540 | 1,487.37 | 2,974.7 |
| LLM few-shot | 0.534 | 0.303 | 0.387 | 0.556 | 1,641.62 | 3,283.2 |
| **Hybrid (ours)** | **0.974** | **0.956** | **0.965** | -- | **<60** | -- |

## Confusion Matrix Details

### Zero-shot
- TP: 51, FP: 50, FN: 180, TN: 219
- The LLM misses 77.9% of noisy samples (FN = 180 / 231)

### Few-shot
- TP: 70, FP: 61, FN: 161, TN: 208
- Few-shot improves recall slightly (30.3% vs 22.1%) but still misses
  about 70% of noise

---

## Key Findings

1. **Pure LLM substantially underperforms** (F1: 0.307 / 0.387 vs 0.965).
2. **Root cause**: the LLM cannot recall 21,954 annotation patterns
   → severe recall failure.
3. **Speed**: rules are ~13,000–15,000× faster than LLM
   (0.11 s vs 1,487–1,642 s).
4. **Few-shot helps marginally**: +8 percentage-point recall, but still
   far from usable (30.3% recall).

---

## Full Pipeline Results (5,000 sample subset)

| Metric | Value |
|--------|-------|
| Total samples (after dedup) | 4,965 |
| Removed (Filter 1 + Filter 2) | 2,576 (51.88%) |
| Kept | 2,389 |
| Pipeline time | ~1.4 s |

### Noise Breakdown

| Noise Type | Count | % of dataset |
|------------|-------|:------------:|
| Unnecessary Annotations | 2,122 | 42.74% |
| No Relevance | 201 | 4.05% |
| Syntax Error | 107 | 2.16% |
| Non-English Literal | 66 | 1.33% |
| Ambiguous Data Type | 63 | 1.27% |
| Missing Implementation | 12 | 0.24% |
| Empty Exception | 5 | 0.10% |

---

## Reproduction

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://tokenhub.tencentmaas.com/v1"

python3 experiments/run_baselines.py \
    --input_csv data/sample_5000.csv \
    --sample_size 500 \
    --output_dir experiments/results \
    --model deepseek-v4-flash
```

## Files

- `baseline_results.json` -- numeric results
- `labeled_samples.csv` -- per-sample predictions (500 rows)
- `run_log.txt` -- full execution log
