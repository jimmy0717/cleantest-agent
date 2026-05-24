# Datasets

This directory contains the datasets used by CleanTest-Agent for
development, testing, and the four-way comparison experiment reported in
[`report/main.tex`](../report/main.tex) Section&nbsp;7.

## Files

### `sample_5000.csv` (5.1 MB)

A 5,000-row stratified random subset of the **Methods2Test** dataset,
covering all eight noise types from the CleanTest taxonomy in roughly
their natural proportions. Used for:

- the 500-sample sub-experiment that produced the headline F1 = 0.965
  vs.&nbsp;0.387 result (`experiments/run_baselines.py` draws a further
  stratified 500-sample subset from this file with `seed=42`);
- the 36-test-case unit-test suite under
  [`tests/`](../tests/) (`tests/fixtures/` contains a 50-row miniature);
- end-to-end smoke tests in [`Makefile`](../Makefile) (`make test`).

#### Columns

| Column | Type | Description |
|---|---|---|
| `target` | string | Java unit test method body, including `@Test` annotation |
| `src_fm` | string | Focal method body (the production code under test) |
| `condition_cover_rate` | float ∈ [0, 1] | Branch coverage of the test against the focal method, measured by JaCoCo (LessIsMore-FSE2025 release; absent in the original Methods2Test) |
| `noise_type` | string &#124; null | Ground-truth noise label from the CleanTest paper (one of the eight types, or null for clean samples) |

#### Stratification

Sampling is stratified by `noise_type` so the subset preserves the
original distribution of noise categories: `unnecessary_annotation`
(~43%), `clean` (~54%), `syntax_error`, `non_english_literal`, and the
remaining minor categories (`empty_exception`, `missing_implementation`,
`ambiguous_data_type`, `no_relevance`, `low_coverage`).

## Provenance

`sample_5000.csv` is derived from the
**LessIsMore-FSE2025** replication package, which is the cleaned and
coverage-labelled re-release of the original **Methods2Test** dataset:

- **Original Methods2Test**: Tufano et&nbsp;al. (2022),
  *Methods2Test: A dataset of focal methods mapped to test cases*
  ([arXiv:2203.12776](https://arxiv.org/abs/2203.12776),
  [microsoft/methods2test](https://github.com/microsoft/methods2test) on
  GitHub). Contains 780,944 test cases mined from 91,385 open-source
  Java projects on GitHub. Released under the **MIT License**.
- **LessIsMore-FSE2025**: Zhang et&nbsp;al. (2025),
  *Less is More: On the Importance of Data Quality for Unit Test
  Generation* (FSE 2025 Distinguished Paper Award;
  [arXiv:2502.14212](https://arxiv.org/abs/2502.14212)). Adds the
  `condition_cover_rate` column from JaCoCo measurements and the
  `noise_type` ground-truth labels used by the CleanTest pipeline.

Both upstream sources allow redistribution of derivative subsets under
their respective open-source licenses; we redistribute this 5,000-row
subset under the same MIT terms inherited from Methods2Test (see
[`../LICENSE`](../LICENSE)). When using `sample_5000.csv`, please cite
both original works:

```bibtex
@inproceedings{tufano2022methods2test,
  title={Methods2Test: A dataset of focal methods mapped to test cases},
  author={Tufano, Michele and Drain, Dawn and Svyatkovskiy, Alexey and Sundaresan, Neel},
  booktitle={Proceedings of the 19th International Conference on Mining Software Repositories},
  pages={299--303},
  year={2022}
}

@inproceedings{zhang2025cleantest,
  title={Less is More: On the Importance of Data Quality for Unit Test Generation},
  author={Zhang, Junwei and Hu, Xing and Gao, Shan and Xia, Xin and Lo, David and Li, Shanping},
  booktitle={Proceedings of the 33rd ACM International Conference on the Foundations of Software Engineering (FSE)},
  year={2025},
  note={Distinguished Paper Award; arXiv:2502.14212}
}
```

## Datasets NOT included in this repository

To keep the repository lightweight and avoid redistributing data whose
license we have not personally verified, the following larger datasets
must be downloaded separately by users who want to reproduce
end-to-end:

| Dataset | Size | How to obtain |
|---|---|---|
| Full LessIsMore-FSE2025 `filter_train.csv` (469,174 rows, used to train Filter&nbsp;3 model mode in §7.5 of the paper) | ~850 MB | See the LessIsMore-FSE2025 replication package linked from the [original paper's arXiv](https://arxiv.org/abs/2502.14212) |
| Full Methods2Test (780,944 test cases) | ~3 GB | [github.com/microsoft/methods2test](https://github.com/microsoft/methods2test) |
| Filter&nbsp;3 fine-tuned Qwen2.5-Coder-0.5B checkpoint (~1 GB) | --- | Released separately via Hugging&nbsp;Face / ModelScope (see the model card under `skills/cleantest-coverage-filter/references/model-card.md`) |

## Reproducibility

The 500-sample stratified split used in §7 of the paper is fully
deterministic: `experiments/run_baselines.py --seed 42 --sample_size 500`
will reproduce the exact same row selection given `sample_5000.csv` as
input. The per-sample predictions (rule-based, zero-shot LLM, few-shot
LLM, hybrid) are archived under
[`experiments/results/labeled_samples.csv`](../experiments/results/labeled_samples.csv).
