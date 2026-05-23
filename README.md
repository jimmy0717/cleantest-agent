# CleanTest-Agent

A multi-agent skill-orchestrated system that cleans noisy unit test training
data using a rule-based pipeline with selective LLM enhancement. This is the
final-project artifact for the *Software Requirements Analysis and System
Design* course at the School of Software, Beihang University.

- Python 3.10+
- 36 pytest test cases (all passing on Python 3.10/3.11/3.12 in GitHub Actions)
- F1 = 0.965 on a 500-sample stratified subset of Methods2Test, vs. 0.387 for
  the best pure-LLM baseline (DeepSeek-V4-Flash few-shot)
- MIT license

Quick links: [Quick Start](#quick-start) ·
[Results](#results) ·
[Architecture](#architecture) ·
[Skills Usage](#code-assistant-integration) ·
[Paper](report/main.tex)

## For Course Reviewers

This repository is the submission artefact for the *Software Requirements
Analysis and System Design* final project. The deliverables map to the
following entry points:

| Deliverable | Location |
|---|---|
| Research report (LaTeX source, ≥ 50 pages) | [`report/main.tex`](report/main.tex), bibliography [`report/references.bib`](report/references.bib) |
| Compiled report (PDF) | [`report/Final Report-V3.pdf`](report/) |
| Slides (≤ 10 pages, 3-min talk) | [`ppt/slides.md`](ppt/slides.md) and [`ppt/PPT大纲.md`](ppt/PPT大纲.md) |
| Reproducible code | this repository (`cleantest_agent/`, `skills/`, `tests/`) |
| Test suite (36 cases) | [`tests/`](tests/), `make test` |
| CI pipeline | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| Real DeepSeek API experiments | [`experiments/run_baselines.py`](experiments/run_baselines.py); results under `experiments/results/` |
| Filter 3 model-mode training | [`main.ipynb`](main.ipynb), scripts under [`skills/cleantest-coverage-filter/scripts_paddle/`](skills/cleantest-coverage-filter/scripts_paddle/), held-out metrics under `experiments/results/coverage_run/` |
| Code-assistant skill bundles | [`skills/`](skills/), each with its own `SKILL.md` |
| Skill installation guide | [`docs/skill-distribution-guide.md`](docs/skill-distribution-guide.md) |
| Code-assistant usage guide | [`docs/code-assistant-guide.md`](docs/code-assistant-guide.md) |
| Baidu AI Studio training guide | [`docs/training-on-baidu-aistudio.md`](docs/training-on-baidu-aistudio.md) |

## Background

The [CleanTest paper](https://arxiv.org/abs/2502.14212) (FSE 2025
Distinguished Paper Award) reports that 43.52% of the Methods2Test dataset
(780,944 test cases from 91,385 projects) contains noisy samples, and that
filtering this noise improves downstream branch coverage by an average of
67.46% across CodeBERT, AthenaTest, StarCoder, and CodeLlama-7B.

A natural question is whether a single LLM call per sample can replace the
rule-based pipeline. We evaluated this on real DeepSeek-V4-Flash API calls
and found that it cannot — the answer is reported below.

## Results

DeepSeek-V4-Flash on 500 stratified samples (231 noise / 269 clean):

| Method | Precision | Recall | F1 | Time (500 samples) |
|--------|:---------:|:------:|:----:|:---------:|
| Rule-based (ours) | 1.000 | 1.000 | 1.000 | 0.11 s |
| LLM zero-shot | 0.505 | 0.221 | 0.307 | 1,487 s |
| LLM few-shot | 0.534 | 0.303 | 0.387 | 1,642 s |
| Hybrid (ours) | 0.974 | 0.956 | 0.965 | < 60 s |

Key findings:

- Pure LLM zero-shot misses 77.9% of noisy samples (recall = 0.221).
- Rules are roughly 13,000–15,000× faster than the LLM baselines on this task.
- LLM failure is concentrated on annotation noise, where it cannot recall the
  21,954-pattern dictionary used by the rule-based filter.
- The hybrid pipeline keeps rules as the primary classifier and queries the
  LLM only on the ~12.7% of samples where AST name matching is inconclusive.
- A 5-rule reflection mechanism (applied only inside Filter 2's LLM stage)
  changed 7 out of 45 zero-overlap verdicts (15.6% change rate), rescuing
  5 samples (11.1% rescue rate) with 6/7 (85.7%) of the changes verified
  correct by manual inspection.

## Architecture

```
User / Coding Assistant
     |  natural-language trigger ("clean my test data")
     v
+-----------------------------------+
|  Orchestrator skill               |
|  (cleantest-pipeline)             |
+-----+----------+--------+---------+
      |          |        |
      v          v        v
+----------+ +-----------+ +--------------+
| Filter 1 | | Filter 2  | | Filter 3     |
| Syntax   | | Relevance | | Coverage     |
|          | |           | |              |
| AST +    | | Name      | | Qwen2.5-     |
| Aho-     | | match +   | | Coder-0.5B   |
| Corasick | | LLM       | | regression   |
| (21,954  | | fallback  | | (model mode) |
| patterns)| |           | |              |
+----+-----+ +-----+-----+ +------+-------+
     |             |              |
     +-------------+--------------+
                   |
                   v
         Clean dataset + noise report
```

Each filter is an independent Agent Skill (SKILL.md protocol) — composable,
testable, and invocable via natural language.

## Quick Start

### Install and run (no API needed)

```bash
git clone https://github.com/jimmy0717/cleantest-agent.git
cd cleantest-agent

# Recommended: editable install (registers the `cleantest_agent` package
# and the `cleantest` console script, and ships the 21,954-pattern
# dictionary as package data)
pip install -e ".[dev]"

# Run pipeline on the bundled 5,000-row sample (rules only)
cleantest --input_csv data/sample_5000.csv --output_dir output/
# Equivalent:
# python -m cleantest_agent.pipeline --input_csv data/sample_5000.csv --output_dir output/

# Run tests
make test    # 36 tests, all passing
```

If you only need the runtime (no test/lint tooling), use `pip install -e .`
or `pip install -r requirements.txt` instead of `".[dev]"`.

For users who want to drop the four skills into a coding assistant
**without cloning this repository**, see
[docs/skill-distribution-guide.md](docs/skill-distribution-guide.md).

### Run the LLM comparison experiment

```bash
# Configure any OpenAI-compatible endpoint
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"   # or any compatible endpoint

# Run the full experiment (500 samples, ~50 minutes)
python experiments/run_baselines.py \
    --input_csv data/sample_5000.csv \
    --sample_size 500 \
    --model deepseek-chat
```

### Install as coding-assistant skills

```bash
make install   # Copies skills to ~/.codebuddy/skills/

# Then in your coding assistant, simply ask:
#   "Help me clean this unit test training dataset"
#   "Filter noisy tests from my CSV"
#   "Check if this test is relevant to the focal method"
```

## Code Assistant Integration

Works with CodeBuddy, Claude Code, Cursor, and any assistant that supports the
SKILL.md protocol.

| Skill | What it does | Trigger |
|-------|--------------|---------|
| `cleantest-pipeline` | Full pipeline orchestration | "clean test data", "run cleantest" |
| `cleantest-syntax-filter` | Syntax noise detection (AST + Aho-Corasick) | "check syntax noise" |
| `cleantest-relevance-filter` | Test–focal method relevance + reflection | "check test relevance" |
| `cleantest-coverage-filter` | Branch coverage prediction | "predict coverage" |

See [docs/code-assistant-guide.md](docs/code-assistant-guide.md) for detailed
usage.

## Why a Pure LLM Falls Short

Consider a focal method whose only "noise" is annotation metadata:

```java
@ApiOperation(value = "Get all users")
@GetMapping("/api/users")
public List<User> getAllUsers() {
    return userRepository.findAll();
}
```

| | Rules (Aho-Corasick) | LLM (DeepSeek-V4-Flash) |
|---|---|---|
| Verdict | NOISE | CLEAN |
| Reason | Matches `@ApiOperation` in 21,954-pattern dictionary | "Standard Spring annotation, looks normal" |
| Time | < 0.01 ms | ~3,000 ms |
| Cost | 0 | API tokens |

The LLM does not know that `@ApiOperation` is "unnecessary for test
generation training" — that is a domain-specific definition derived from
expert interviews in the original CleanTest study. Encoding the full
21,954-pattern dictionary into a prompt is not feasible.

## Project Structure

```
cleantest-agent/
├── cleantest_agent/            # Installable Python package (`pip install -e .`)
│   ├── __init__.py             # Public API: run_pipeline, run_syntax_filter, ...
│   ├── pipeline.py             # Orchestrator (Aho-Corasick + 3 filters)
│   ├── parser_utils.py         # tree-sitter AST utilities
│   ├── llm_client.py           # OpenAI-compatible LLM wrapper
│   ├── data_loader.py          # CSV I/O
│   ├── report_generator.py     # JSON + Markdown reports
│   └── data/                   # Bundled package data
│       └── noise_modifier_fm.txt   # 21,954-pattern dictionary
├── skills/                     # 4 Agent Skills (SKILL.md + scripts)
│   ├── cleantest-pipeline/
│   ├── cleantest-syntax-filter/
│   ├── cleantest-relevance-filter/
│   └── cleantest-coverage-filter/
├── tests/                      # 36 pytest test cases
├── experiments/                # Baseline comparison scripts
│   ├── run_baselines.py        # Real API experiment
│   ├── simulate_baselines.py   # Offline simulation (legacy)
│   └── results/                # Experiment data (JSON + CSV)
├── data/                       # Sample dataset (5,000 rows)
├── docs/                       # User-facing guides
│   ├── code-assistant-guide.md
│   └── skill-distribution-guide.md
├── .github/workflows/ci.yml    # CI: Python 3.10/3.11/3.12 matrix
├── report/                     # LaTeX research paper (ACM format)
├── pyproject.toml              # Package metadata + console script
└── Makefile                    # dev-install, test, lint, install, clean
```

## Technical Notes

| Component | Technology | Reason |
|-----------|-----------|--------|
| Pattern matching | Aho-Corasick automaton | ~11.5× pipeline speedup over linear scan of 21,954 patterns |
| AST parsing | tree-sitter (C-based) | Error-tolerant, < 0.1 ms per method, concrete syntax trees |
| Coverage filter | Label scan (default) or fine-tuned Qwen2.5-Coder-0.5B regression (optional model mode) | Label mode is used by all reported numbers in §7.5; model mode validation is reported in §7.5 (`tab:filter3-model-mode`). Replaces the original CleanTest's CodeGPT recipe. |
| LLM integration | OpenAI-compatible SDK | Works with GPT-4o-mini, DeepSeek, Qwen, Claude |
| Reflection | 5-rule structured self-correction | Reduces false removals on borderline indirect tests |
| Skills protocol | SKILL.md | Cross-IDE compatible (CodeBuddy, Claude Code, Cursor) |

## Citation

```bibtex
@misc{yang2026cleantest-agent,
  title  = {CleanTest-Agent: A Multi-Agent Skill-Orchestrated System for
            Unit Test Training Data Quality Assurance},
  author = {Yang, Yong},
  year   = {2026},
  howpublished = {\url{https://github.com/jimmy0717/cleantest-agent}}
}
```

Based on:

- Zhang et al., *Less is More: On the Importance of Data Quality for Unit
  Test Generation*, FSE 2025 (Distinguished Paper Award).
  <https://arxiv.org/abs/2502.14212>

## License

MIT.
