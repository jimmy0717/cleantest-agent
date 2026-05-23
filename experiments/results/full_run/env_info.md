# Reproduction metadata for full Methods2Test run

## Date
2026-05-18 23:49:11 CST

## Hardware
Darwin JYYONGYANG-MC1 24.6.0 Darwin Kernel Version 24.6.0: Mon Jul 14 11:29:54 PDT 2025; root:xnu-11417.140.69~1/RELEASE_ARM64_T8122 arm64
Apple M3
Physical RAM: 16.0 GB

## Python
Python 3.9.6

## Key dependencies
pandas 2.3.3
tree-sitter unknown
pyahocorasick unknown
tqdm 4.67.1

## Input dataset
Source: LessIsMore-FSE2025 replication package (Zenodo DOI: 10.5281/zenodo.15347368)
Path:   dataset/training_dataset/all_dataset/all_train.csv
Rows:   624,022 (before dedup) -> 593,953 (after dedup on `target`)
SHA-256: 2a1af33543a3fd9425117d17f799bd815d0585b58766c44f838e10d270c18836

## Reproduction command
```bash
python3 -m cleantest_agent.pipeline \
    --input_csv path/to/all_train.csv \
    --output_dir experiments/results/full_run \
    --skip_coverage
```

## Wall-clock time
real 158.04 s  (2 min 38 sec)

## Files in this directory

- `summary.md` — human-readable noise breakdown
- `noise_report.json` — machine-readable per-noise-type counts
- `filtered_data.sample.csv` — first 1,000 rows of the filtered output, kept for spot-checking
- `run_log.txt` — full execution log

The full `filtered_data.csv` (~267 MB, 273,383 rows) is reproducible
from the input CSV plus the reproduction command above and is not
checked in to keep the repository small.
