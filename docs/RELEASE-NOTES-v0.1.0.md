# CleanTest-Agent v0.1.0

First public release.

CleanTest-Agent removes noisy `(focal_method, test_case)` pairs from
unit-test training corpora such as Methods2Test, ATLAS, and any dataset
that follows the same schema. It is a from-scratch reimplementation of
the CleanTest pipeline (Zhang et al., FSE 2025 Distinguished Paper),
restructured as four composable Agent Skills that drop into CodeBuddy,
Claude Code, Cursor, or any assistant that follows the SKILL.md
protocol.

This release covers the full three-filter pipeline, the fine-tuned
Qwen2.5-Coder-0.5B coverage regressor, the 36-test pytest suite, and
the four shippable skills.

## Highlights

- **Three-filter pipeline** -- syntax (AST + Aho-Corasick over a
  21,954-pattern dictionary), relevance (AST name matching with an
  optional 5-rule LLM reflection step), and coverage (JaCoCo-label
  scan or model-mode regression).
- **Hybrid mode beats pure-LLM** -- F1 0.965 in under 60 s on a
  500-sample stratified subset of Methods2Test, versus 0.307 / 0.387
  for LLM zero-shot / few-shot baselines that take ~25 minutes each.
- **Filter 3 without JaCoCo** -- a fine-tuned Qwen2.5-Coder-0.5B
  predicts branch coverage with held-out MAE 0.0309 (~2.6x lower than
  the CodeGPT baseline reported in the original paper).
- **Four SKILL.md skills** -- `cleantest-pipeline`,
  `cleantest-syntax-filter`, `cleantest-relevance-filter`, and
  `cleantest-coverage-filter`. Install with `make install`.
- **Cost** -- ~$4.5 to clean the full 593,953-sample Methods2Test
  corpus end-to-end with DeepSeek-V4-Flash, versus ~$35-58 for a
  single-LLM-per-sample pipeline.

## Installation

```bash
git clone https://github.com/jimmy0717/cleantest-agent.git
cd cleantest-agent
pip install -e ".[dev]"
```

To install the four skills into the local CodeBuddy directory:

```bash
make install
```

## Quick start

```bash
# Bundled 5,000-row sample, no API needed:
cleantest --input_csv data/sample_5000.csv --output_dir output/

# With the optional LLM relevance check + reflection:
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
cleantest --input_csv data/sample_5000.csv \
          --output_dir output/ \
          --llm_enhance --reflection
```

A noise report is written to `output/noise_report.json` plus a
human-readable Markdown summary.

## What is included

- `cleantest_agent/` -- installable Python package with the
  orchestrator, tree-sitter AST utilities, OpenAI-compatible LLM
  wrapper, and the bundled 21,954-pattern annotation dictionary.
- `skills/` -- four SKILL.md skill bundles, each independently usable.
- `tests/` -- 36 pytest cases covering each filter, the orchestrator,
  and the report generator.
- `experiments/` -- baseline runner with real DeepSeek API calls,
  per-sample predictions for the 500-sample evaluation, and the
  end-to-end Filter 3 training notebook.
- `data/sample_5000.csv` -- a 5,000-row stratified subset of
  Methods2Test, redistributed under the upstream MIT licence.
- `docs/` -- skill distribution guide, code-assistant usage guide,
  Baidu AI Studio training guide, and the hero-image prompt.
- `report/` -- the 67-page LaTeX paper (acmart `acmlarge,nonacm`).
- `.github/workflows/ci.yml` -- CI matrix on Python 3.10 / 3.11 / 3.12.

## Reproducibility

The four numeric claims in the README are reproducible from this
release:

| Claim | How to reproduce |
|---|---|
| F1 = 1.000 (rule-based) on the 500-sample subset | `python experiments/run_baselines.py --method rules` |
| F1 = 0.965 (hybrid) on the same subset | `python experiments/run_baselines.py --method hybrid` (requires `OPENAI_API_KEY`) |
| MAE = 0.0309 (Qwen 0.5B Filter 3) | `experiments/main-final.ipynb` end-to-end, or `experiments/results/coverage_run/test_metrics.json` for the archived numbers |
| Wall-clock < 3 min on Methods2Test | `cleantest --input_csv methods2test_full.csv --output_dir out/` after running the upstream Methods2Test export |

The 500-sample stratified subset, the per-sample predictions for every
baseline, and the full Filter 3 training metrics are checked into
`experiments/results/`.

## Compatibility

- Python 3.10, 3.11, 3.12 (CI-tested).
- macOS, Linux, Windows (tree-sitter wheels available for all three).
- Filter 3 *model mode* requires PyTorch >= 2.1 and a Hugging Face
  account with access to `Qwen/Qwen2.5-Coder-0.5B`. The default
  *label mode* has no extra dependencies.
- Any OpenAI-compatible chat endpoint works for the relevance LLM
  step. The numbers in the paper are from DeepSeek-V4-Flash.

## Known limitations

- The annotation dictionary is Java-only. C# / Kotlin / Python test
  corpora work with Filter 1's AST checks but will not benefit from
  the 21,954-pattern Aho-Corasick scan.
- Filter 3 *model mode* is trained on Java JaCoCo labels; predictions
  on non-Java tests are not validated.
- Reflection on Filter 2 is *opt-in* and *additive*. The headline
  F1 = 0.965 was measured *without* reflection; enabling it produced
  a small recall improvement on a 50-sample borderline subset that
  is too small to claim a corpus-level gain. See report Section 6.2.
- Filter 2 LLM mode currently issues one request per borderline
  sample; batched requests are tracked as a future improvement
  (report Section 9.3).

## Datasets and licences

- Code: MIT.
- `data/sample_5000.csv`: derivative of Microsoft Methods2Test (MIT),
  redistributed under the same terms; see `data/README.md` for the
  full attribution.
- The 21,954-pattern annotation dictionary in
  `cleantest_agent/data/noise_modifier_fm.txt` is reconstructed from
  the public CleanTest replication package (FSE 2025) and is
  redistributed under MIT.

## Citation

If you use CleanTest-Agent in academic work, please cite both the
original CleanTest paper and this implementation:

```bibtex
@inproceedings{zhang2025cleantest,
  title     = {Less is More: On the Importance of Data Quality for Unit Test Generation},
  author    = {Zhang, Junwei and Hu, Xing and Gao, Shan and Xia, Xin and Lo, David and Li, Shanping},
  booktitle = {Proceedings of the 33rd ACM International Conference on the Foundations of Software Engineering (FSE)},
  year      = {2025},
  note      = {Distinguished Paper Award; arXiv:2502.14212}
}

@misc{yang2026cleantestagent,
  title  = {{CleanTest-Agent}: A Multi-Agent Skill-Orchestrated System for Unit Test Training Data Quality Assurance},
  author = {Yang, Yong},
  year   = {2026},
  howpublished = {\url{https://github.com/jimmy0717/cleantest-agent}}
}
```

## Acknowledgements

- Zhang et al. for the original CleanTest definitions and the public
  replication package.
- Microsoft for releasing Methods2Test under MIT.
- The Qwen team for releasing Qwen2.5-Coder-0.5B under Apache 2.0.
- Reviewers in the *Software Requirements Analysis and System Design*
  course at the School of Software, Beihang University, whose
  feedback shaped the final structure of the report and the skills.

## What's next

Tracked for a follow-up release (see `report/main.tex` Section 9.3
for the full list):

- Batched Filter 2 LLM requests, expected to reduce wall-clock by
  approximately 5x on the borderline subset.
- Multi-language Filter 1 (extend the Aho-Corasick dictionary beyond
  Java).
- A `cleantest-eval` skill that takes a labelled validation slice and
  reports precision / recall / F1 directly inside the assistant.

Issues and pull requests are welcome -- see `CONTRIBUTING.md` for
the development workflow.

---

**Full diff**: this is the first public release; there is no prior tag.
**Git tag**: `v0.1.0`
**Date**: 2026-05-24
