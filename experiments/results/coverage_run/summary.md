# Filter 3 (Coverage) Run on `filter_train.csv`

**Date**: 2026-05-18  
**Hardware**: Apple M3, 16 GB RAM, macOS (arm64)  
**Software**: Python 3.9.6, pandas 2.3.3

---

## Input dataset

- File: `dataset/training_dataset/filter_dataset/filter_train.csv`
- Source: LessIsMore-FSE2025 replication package (Zenodo DOI 10.5281/zenodo.15347368)
- SHA-256: `8eaed383a582cfe43a545d8f8e95213734bb639b8b4fba3db17a63e9b02cf87f`
- Rows: **469,174** (already passed Filter 1 + Filter 2 in the original CleanTest pipeline)
- Columns: `idx, src_fm, target, condition_cover_rate, line_cover_rate`

## Coverage label statistics

| metric | value |
|---|---:|
| min | 0.0110 |
| max | 1.9100 |
| mean | 0.1271 |
| median | 0.1080 |
| std | 0.1007 |

Note: `min = 0.011 > 0.01` confirms that `filter_train.csv` is the post-CleanTest output produced with the paper's default threshold of 0.01 — every sample whose `condition_cover_rate < 0.01` had already been removed.

## Threshold sensitivity sweep

| threshold | removed | removed % | kept | wall-clock (s) | throughput (samples/s) |
|---:|---:|---:|---:|---:|---:|
| 0.010 | 0 | 0.00% | 469,174 | 6.55 | 71,672 |
| 0.050 | 84,021 | 17.91% | 385,153 | 6.43 | 72,932 |
| 0.100 | 212,059 | 45.20% | 257,115 | 6.42 | 73,042 |
| 0.150 | 327,016 | 69.70% | 142,158 | 6.41 | 73,224 |
| 0.200 | 400,999 | 85.47% | 68,175 | 6.43 | 72,914 |
| 0.300 | 448,842 | 95.67% | 20,332 | 6.49 | 72,306 |

## Reproduction

```python
from cleantest_agent.pipeline import run_coverage_filter
from cleantest_agent.report_generator import NoiseReport
import pandas as pd
df = pd.read_csv('filter_train.csv', low_memory=False)
for t in [0.01, 0.05, 0.10, 0.15, 0.20, 0.30]:
    report = NoiseReport(total_samples=len(df))
    rm = run_coverage_filter(df, report, threshold=t)
    print(t, len(rm), len(rm)/len(df))
```

## Files in this directory

- `coverage_sweep.json` — machine-readable sweep results
- `run_log.txt` — clean run log (no progress-bar noise)
- `summary.md` — this human-readable summary
