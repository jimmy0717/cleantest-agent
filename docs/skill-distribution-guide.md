# Skill Distribution Guide

This document is for **external users** who want to install one or more
CleanTest-Agent skills into their coding assistant **without cloning the
full project**, and for maintainers who want to understand the
distribution boundary between the Python package and the four skills.

If you only want to run the pipeline locally as a CLI tool, you can stop
after the first section ("Install the runtime"). If you want a coding
assistant (CodeBuddy, Claude Code, Cursor, ...) to invoke the filters via
natural language, follow the rest of the document.

---

## TL;DR

Two artifacts are distributed independently:

| Artifact | What it ships | Where it lives |
|---|---|---|
| `cleantest-agent` Python package | `cleantest_agent/` source + the 21,954-pattern dictionary as package data | PyPI / `pip install -e .` |
| 4 Agent Skills | `SKILL.md` + thin script wrappers | `skills/cleantest-*/` (copy into `~/.codebuddy/skills/` etc.) |

The skills depend on the package, not the other way round. The package
has zero dependency on the skills directory and can be used as a normal
Python library.

---

## 1. Install the runtime

The skills' scripts all execute `from cleantest_agent.X import ...`, so
the package must be importable in the Python environment your coding
assistant launches subprocesses in.

```bash
# Option A -- once published on PyPI:
pip install cleantest-agent

# Option B -- from a local checkout (today):
git clone https://github.com/jimmy0717/cleantest-agent.git
cd cleantest-agent
pip install -e .
```

Optional extras:

```bash
pip install "cleantest-agent[coverage]"   # Qwen2.5-Coder-0.5B regression model deps
pip install "cleantest-agent[dev]"        # pytest, flake8, mypy
```

Verify:

```bash
python -c "import cleantest_agent; print(cleantest_agent.__version__)"
# X.Y.Z   (e.g. 0.1.1; the version is resolved at import time from
#          the installed distribution metadata, so it always tracks
#          whatever pip installed)

cleantest --help
# usage: cleantest [-h] --input_csv INPUT_CSV --output_dir OUTPUT_DIR ...
```

The 21,954-pattern annotation dictionary
(`cleantest_agent/data/noise_modifier_fm.txt`, ~1.7 MB) is included as
package data via `importlib.resources`, so it remains available even if
the install location is read-only or the user is running inside a venv.

---

## 2. Drop the skills into your coding assistant

Each of the four skills is a self-contained directory under `skills/`
that follows the [SKILL.md protocol](https://github.com/anthropics/skills)
used by CodeBuddy, Claude Code, Cursor, and similar agents.

```
skills/
├── cleantest-pipeline/                 # Orchestrator
│   ├── SKILL.md
│   └── scripts/run_pipeline.py
├── cleantest-syntax-filter/            # Filter 1
│   ├── SKILL.md
│   └── scripts/syntax_filter.py
├── cleantest-relevance-filter/         # Filter 2
│   ├── SKILL.md
│   └── scripts/relevance_filter.py
│   └── scripts/llm_relevance.py
└── cleantest-coverage-filter/          # Filter 3
    ├── SKILL.md
    └── scripts/coverage_predictor.py
```

### 2.1 CodeBuddy

```bash
# All four skills:
cp -r skills/cleantest-* ~/.codebuddy/skills/

# Or only the orchestrator:
cp -r skills/cleantest-pipeline ~/.codebuddy/skills/
```

Then in any CodeBuddy session, ask in natural language:

- "Help me clean this unit test training dataset" → fires `cleantest-pipeline`
- "Check syntax noise in this CSV" → fires `cleantest-syntax-filter`
- "Is this test relevant to the focal method?" → fires `cleantest-relevance-filter`
- "Predict branch coverage for these tests" → fires `cleantest-coverage-filter`

### 2.2 Claude Code

```bash
cp -r skills/cleantest-* ~/.claude/skills/
```

### 2.3 Cursor / other SKILL.md-compatible assistants

Copy the skill directories into whichever location your assistant scans
for skills. The `SKILL.md` frontmatter (`name`, `description`,
`Triggers: ...`) is the only thing the assistant needs to discover the
skill and decide when to invoke it.

### 2.4 Picking individual skills

You do **not** need to install all four. The dependency graph is:

```
cleantest-pipeline ──┬──> cleantest-syntax-filter
                     ├──> cleantest-relevance-filter
                     └──> cleantest-coverage-filter
```

The orchestrator skill calls the three filter skills in sequence, but
each filter skill also runs standalone. Common minimal installs:

| Use case | Install |
|---|---|
| End-to-end pipeline | `cleantest-pipeline` (the orchestrator will discover the filters under the same parent dir) |
| Only annotation/syntax noise detection | `cleantest-syntax-filter` |
| Only relevance check during PR review | `cleantest-relevance-filter` |
| Only coverage prediction in your benchmark loop | `cleantest-coverage-filter` |

---

## 3. Configure the LLM (optional)

Filter 2 (relevance) and the LLM enhancement step in Filter 1 use any
OpenAI-compatible endpoint. Set:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"   # any compatible host
export OPENAI_MODEL="deepseek-chat"                    # default
```

If `OPENAI_API_KEY` is unset, the skills fall back to rule-only mode
without raising an error -- so the pipeline still produces a valid clean
dataset, just without the optional LLM rescue/confirm step.

---

## 4. Smoke test (no API key required)

```bash
# 1. Have the package installed (Section 1)
# 2. Use the bundled sample dataset
cleantest \
    --input_csv data/sample_5000.csv \
    --output_dir output/

# Expected outputs:
#   output/filtered_data.csv   (rows that passed all filters)
#   output/noise_report.json   (per-noise-type counts)
#   output/summary.md          (human-readable report)
# With ~52% of samples flagged as noise, ~80 s wall-clock on a laptop.
```

Or invoke a single filter directly:

```bash
python skills/cleantest-syntax-filter/scripts/syntax_filter.py \
    --input_csv data/sample_5000.csv \
    --output_csv /tmp/syntax_out.csv
```

---

## 5. Updating the skills

Skills are versioned together with the Python package. To upgrade:

```bash
pip install -U cleantest-agent
# Then re-copy the skill directories from a fresh checkout if SKILL.md
# triggers or scripts changed.
```

Because the skill scripts are thin wrappers (~30–80 LOC each) over
package APIs, breaking changes will normally be in the package. The
`SKILL.md` files themselves change only when triggers, prerequisites,
or noise type definitions evolve.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'cleantest_agent'` | Skill scripts running in a different Python env than where the package is installed | Install the package in the env your coding assistant uses; or set `PYTHONPATH` to the repo root |
| `FileNotFoundError: noise_modifier_fm.txt` | Old install where the dictionary was outside the package | Reinstall `cleantest-agent>=0.1.0`; the dict is now package data |
| `RuntimeError: OPENAI_API_KEY not set` (only with `--llm_enhance` / Filter 2) | LLM features explicitly enabled without credentials | Either unset the LLM flag (rule-only mode) or export `OPENAI_API_KEY` and `OPENAI_BASE_URL` |
| Skill not triggered by the assistant | Triggers in `SKILL.md` don't match the user phrasing | Edit the `Triggers:` line in the corresponding `SKILL.md` to add aliases |

---

## 7. Reference

- Repository: <https://github.com/jimmy0717/cleantest-agent>
- Paper: `report/main.tex` (ACM acmart)
- Package API: `cleantest_agent/__init__.py`
  (`run_pipeline`, `run_syntax_filter`, `run_relevance_filter`, `run_coverage_filter`)
- Skill protocol: SKILL.md frontmatter (name + description + Triggers)
- License: MIT
