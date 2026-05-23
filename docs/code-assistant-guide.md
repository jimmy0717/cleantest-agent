# Code Assistant Usage Guide

This document describes how to install and use CleanTest-Agent skills with various AI coding assistants.

## Supported Coding Assistants

| Assistant | Status | Installation Method |
|-----------|--------|-------------------|
| **CodeBuddy** | Tested | Copy to `~/.codebuddy/skills/` |
| **Claude Code** | Compatible | Copy to `~/.claude/skills/` |
| **Cursor** | Compatible | Copy to project `.cursor/skills/` |
| **Other (SKILL.md compatible)** | Should work | Copy to the assistant's skill directory |

## Installation

### Step 1: Install Python Dependencies

```bash
cd cleantest-agent
pip install -r requirements.txt
```

### Step 2: Install Skills

#### Global Install (all projects):

**For CodeBuddy:**
```bash
make install
# This copies all 4 skills to ~/.codebuddy/skills/
```

**For Claude Code:**
```bash
mkdir -p ~/.claude/skills
for s in cleantest-pipeline cleantest-syntax-filter \
         cleantest-relevance-filter cleantest-coverage-filter; do
  cp -R skills/$s ~/.claude/skills/$s
done
```

#### Project-Level Install (current project only):

```bash
mkdir -p .codebuddy/skills
cp -R skills/* .codebuddy/skills/
```

### Step 3: Restart Your Coding Assistant

The assistant scans for new skills on startup. After installation, restart your IDE or coding assistant session.

## How to Use the Skills

### Method 1: Natural Language Trigger (Recommended)

Simply describe what you want to do in natural language. The assistant will automatically detect which skill to invoke based on trigger phrases defined in each `SKILL.md`.

| What You Want | What to Say | Skill Invoked |
|---------------|-------------|---------------|
| Clean a full dataset | "Help me clean this unit test training dataset" | `cleantest-pipeline` |
| Check syntax noise | "Check this code for syntax noise" | `cleantest-syntax-filter` |
| Check test relevance | "Is this test relevant to its focal method?" | `cleantest-relevance-filter` |
| Predict coverage | "Predict the coverage of this test" | `cleantest-coverage-filter` |
| Run full pipeline | "Run the CleanTest pipeline on my CSV" | `cleantest-pipeline` |

**Chinese triggers also work:**
- "帮我清洗这份单元测试数据集"
- "检测语法噪声"
- "检查测试相关性"
- "运行 CleanTest"

### Method 2: CLI (Without Coding Assistant)

```bash
# Full pipeline (no LLM, skip coverage)
python -m cleantest_agent.pipeline \
  --input_csv path/to/data.csv \
  --output_dir ./output \
  --skip_coverage

# Full pipeline with LLM enhancement
export OPENAI_API_KEY="sk-..."
python -m cleantest_agent.pipeline \
  --input_csv path/to/data.csv \
  --output_dir ./output \
  --llm_enhance

# Individual filters
python skills/cleantest-syntax-filter/scripts/syntax_filter.py \
  --input_csv data.csv --output_csv filtered.csv

python skills/cleantest-relevance-filter/scripts/relevance_filter.py \
  --input_csv data.csv --output_csv filtered.csv
```

### Method 3: Invoke Specific Skill by Name

In CodeBuddy, you can also explicitly invoke a skill:

> "Use the cleantest-syntax-filter skill to check my dataset for noisy annotations."

The assistant will read the corresponding `SKILL.md` and follow its instructions.

## Skill Details

### cleantest-pipeline (Orchestrator)

**File:** `skills/cleantest-pipeline/SKILL.md`

**Purpose:** Orchestrates all 3 filters in sequence, generates a noise report.

**Input:** CSV with `src_fm` and `target` columns.

**Output:**
- `filtered_data.csv` — cleaned dataset
- `noise_report.json` — structured statistics
- `summary.md` — human-readable report

### cleantest-syntax-filter (Filter 1)

**File:** `skills/cleantest-syntax-filter/SKILL.md`

**Purpose:** Detects 6 syntactic noise types (N1–N6) from the CleanTest paper, including unnecessary annotations matched against a 21,954-pattern dictionary.

**Key Resources:**
- `references/noise_modifier_fm.txt` — Dictionary of 21,954 annotation patterns
- Uses Aho-Corasick automaton for fast matching

### cleantest-relevance-filter (Filter 2)

**File:** `skills/cleantest-relevance-filter/SKILL.md`

**Purpose:** Checks if test cases are relevant to their focal methods.

**Two-Stage Design:**
1. AST name matching (fast, deterministic)
2. LLM semantic judgment (only for ~12.7% borderline cases)

### cleantest-coverage-filter (Filter 3)

**File:** `skills/cleantest-coverage-filter/SKILL.md`

**Purpose:** Filters samples by branch coverage. Default *label mode* reads the `condition_cover_rate` column from the input CSV; optional *model mode* uses a fine-tuned Qwen2.5-Coder-0.5B regression model when no label is available.

**Requires:** Label mode runs anywhere with pandas. Model mode requires a trained Qwen2.5-Coder-0.5B checkpoint and a GPU; skippable via `--skip_coverage`.

## Example Session (CodeBuddy)

```
User: "I have a CSV file at data/all_train.csv with unit test training
       data. Please clean it using CleanTest to remove noisy samples."

Assistant: [Invokes cleantest-pipeline skill]
"I will run the CleanTest-Agent pipeline on your dataset.
Loaded 593,953 unique samples (after deduplication on the `target` column).
Running Filter 1 (Syntax Noise)... removed 290,685 samples.
Running Filter 2 (Relevance)... removed 29,885 samples.
Filter 3 (Coverage) was skipped (no model provided).
Pipeline complete! 273,383 clean samples saved to output/filtered_data.csv.
See output/summary.md for the full noise report."

User: "What types of noise were found?"

Assistant: [Reads output/noise_report.json]
"Here is the breakdown:
- Unnecessary Annotations: 259,427 (43.68%)
- No Relevance: 29,885 (5.03%)
- Syntax Errors: 16,372 (2.76%)
- Ambiguous Data Type: 10,335 (1.74%)
- Empty Exception: 2,259 (0.38%)
- Non-English: 1,479 (0.25%)
- Missing Implementation: 813 (0.14%)"
```
