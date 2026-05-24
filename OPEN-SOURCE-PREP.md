# Open-Source Release Preparation

This document is the operational checklist for publishing CleanTest-Agent
to a public GitHub repository. It records what has already been done,
what remains for the maintainer (you) to do, and the audit findings
against which each step was decided.

> **Status legend:** done · needs decision · to-do before
> first public push.

---

## 0. Three-stage release strategy

| Stage | Audience | Includes | Status |
|---|---|---|---|
| **1. Code-only minimum** | early adopters of the four Agent Skills | `cleantest_agent/`, `skills/`, `tests/`, `.github/`, `docs/`, `data/sample_5000.csv`, small JSON/MD experiment summaries | ⏳ ready, awaiting first push |
| **2. Paper-companion** | reviewers / academic readers | adds `report/` (LaTeX source + PDF) and a sanitised `experiments/main-final.ipynb` | ⏳ after course submission settles |
| **3. Full reproducibility** | researchers who want to re-train Filter&nbsp;3 | model checkpoint on Hugging&nbsp;Face / ModelScope, full coverage CSV on Zenodo (with DOI) | ⏳ optional |

The repository is structured so all three stages can ship from the same
codebase --- the differences are only what is gitignored vs. committed.

---

## 1. Audit findings (snapshot 2026-05-24)

### 1.1 Personal Identifiable Information --- acceptable as-is

| File | Line(s) | Content | Decision |
|---|---|---|---|
| `pyproject.toml` | 13 | `Yong Yang <yang_qhd@buaa.edu.cn>` | **Keep**: standard package authorship metadata. |
| `report/main.tex` | 108, 115 | `\author{Yong Yang}`, `\email{yang_qhd@buaa.edu.cn}` | **Keep**: academic paper authorship convention; `.edu` email is normal. |
| `ppt/slides.md` | 6, 7, 237 | Author block on title and contact slide | **Keep**: same rationale as paper. |
| `ppt/PPT大纲.md` | 25, 27, 295 | Author block (Chinese outline of the same slides) | **Optional**: this file is a Chinese-language scratch outline; you may exclude it from the open-source mirror via `.gitignore` if you prefer to publish only the English `slides.md`. |

No API keys, tokens, or passwords were found anywhere in the tracked
sources.

### 1.2 Internal path leakage --- remediated

| File | Original | Fix applied |
|---|---|---|
| `experiments/results/coverage_run/training_metrics.json` | `"base_model": "/home/aistudio/work/cleantest-agent/.ms_cache/Qwen/Qwen2___5-Coder-0___5B"` | Replaced with the public model identifier `"Qwen/Qwen2.5-Coder-0.5B"` so reproducers can resolve it directly via Hugging&nbsp;Face / ModelScope. |
| `docs/training-on-baidu-aistudio.md` | nine `/home/aistudio/...` paths | **Intentionally kept**: this document IS the AI&nbsp;Studio walkthrough; the paths are AI&nbsp;Studio's standard mount points, not personal directories. |
| `experiments/main-final.ipynb` | 48 `/home/aistudio/...` references in cell sources and outputs | **Intentionally kept** for the paper-companion stage: the notebook reproduces the AI&nbsp;Studio session. Stage&nbsp;1 release excludes the notebook entirely; stage&nbsp;2 release ships it as-is because the paths are documented to be AI&nbsp;Studio mount points. |

### 1.3 Large files --- excluded via `.gitignore`

| File | Size | Why excluded |
|---|---|---|
| `experiments/results/coverage_run/test_pred_a800.csv` | 50 MB | Per-sample inference dump, regenerable from the released checkpoint. |
| `experiments/results/coverage_run/train_a800.log` | 1.4 MB | Verbose training log; `metrics.jsonl` (114 KB) is the curated subset retained for the paper. |
| `paper/Less is more.pdf` | 1.1 MB | Third-party paper (Zhang et&nbsp;al. FSE 2025); copyright is ACM's, cannot be redistributed. |
| `期末大作业要求.docx`, `课程分数构成与期末作业内容.png`, `方案细化.md`, `cleantest-agent-v*.zip` | < 500 KB total | Course-internal materials kept locally beside the repo but never published. |

`.gitignore` was extended (see commit history) so any future
`git add .` will silently skip these.

### 1.4 Duplicate data --- deduplicated

`skills/cleantest-syntax-filter/references/noise_modifier_fm.txt`
(1.7 MB) was a verbatim copy of `cleantest_agent/data/noise_modifier_fm.txt`
already shipped as Python package data. The duplicate has been removed
and replaced with a small README pointing to the canonical location.

---

## 2. Pre-push checklist (run these before the first `git push`)

### 2.1 Sanity-check the working tree

```bash
cd cleantest-agent

# Confirm the .gitignore actually excludes everything intended:
git status --ignored

# Should show test_pred_a800.csv, train_a800.log, paper/, *.zip,
# 方案细化.md, etc. under "Ignored files".

# Confirm there is no untracked file that *should* be tracked:
git status

# Should be empty modulo the OPEN-SOURCE-PREP.md / data/README.md /
# noise_modifier_fm.txt.README files added in this session.
```

### 2.2 Run the full test suite locally

```bash
make test          # 36 tests, all should pass
make lint          # flake8 + mypy
```

(Replicates exactly what GitHub Actions will run on the public repo.)

### 2.3 Smoke-test the package install on a clean Python env

```bash
python -m venv /tmp/cta-smoke
source /tmp/cta-smoke/bin/activate
pip install -e .
python -c "from cleantest_agent.pipeline import run_pipeline; print('OK')"
deactivate && rm -rf /tmp/cta-smoke
```

This catches `MANIFEST.in` / `pyproject.toml` packaging errors that
locally never surface (e.g. missing `cleantest_agent/data/*.txt`
inclusion).

### 2.4 Verify no secrets in git history

```bash
# A literal scan of every committed blob for things that look like keys.
git log --all -p | grep -iE "sk-[a-z0-9]{20}|api_key.*=.*['\"][a-z0-9]" | head
# Should print nothing.
```

If anything shows up, rotate the key first, then rewrite history with
`git filter-repo --replace-text patterns.txt` before going public.

---

## 3. GitHub repository setup (one-shot)

Once the local tree is clean:

```bash
# Create a new public repo (replace <user> with your GitHub username):
gh repo create <user>/cleantest-agent --public \
    --description "Multi-agent skill-orchestrated test data cleaning pipeline (FSE'25 CleanTest, faithfully ported with Reflection + a fine-tuned Qwen2.5-Coder-0.5B coverage filter)" \
    --homepage "https://arxiv.org/abs/2502.14212"

# Push:
git remote add origin git@github.com:<user>/cleantest-agent.git
git push -u origin main
```

### 3.1 Recommended repository topics (search visibility)

Add via Settings → Topics:

```
agent-skills, software-testing, data-quality, code-analysis,
unit-test-generation, methods2test, llm-agents, claude-code,
codebuddy, fine-tuning, qwen, code-llm
```

### 3.2 First release

```bash
gh release create v0.1.0 \
    --title "v0.1.0 -- initial public release" \
    --notes-file RELEASE-NOTES-v0.1.0.md
```

(Suggested release notes are in section 4 below.)

---

## 4. Release notes for v0.1.0

```markdown
# CleanTest-Agent v0.1.0 -- initial public release

## What's in this release

- **4 composable Agent Skills** (`cleantest-pipeline`, `cleantest-syntax-filter`,
  `cleantest-relevance-filter`, `cleantest-coverage-filter`) targeting the
  SKILL.md protocol used by CodeBuddy, Claude Code, and Cursor.
- **Faithful Python port of the CleanTest pipeline** (Zhang et al., FSE 2025
  Distinguished Paper Award) with two original engineering contributions:
  1. an Aho-Corasick automaton for the 21,954-pattern annotation dictionary,
     yielding ~11.5× pipeline speedup;
  2. a fine-tuned Qwen2.5-Coder-0.5B replacing the original CodeGPT
     coverage filter (held-out MAE 0.0309, ~2.6× lower than CodeGPT).
- An **opt-in 5-rule Reflection mechanism** for Filter 2's LLM stage,
  inspired by Lab 1 of BUAA's Software Requirements Analysis & System
  Design course.
- A **36-case pytest suite** running on Python 3.10/3.11/3.12 in GitHub
  Actions CI.
- A **stratified 5,000-row Methods2Test subset** (`data/sample_5000.csv`)
  covering all eight CleanTest noise types in their natural proportions.
- The **full LaTeX source of the companion 67-page paper** under
  `report/` (acmart `acmlarge`).

## What's NOT in this release (and how to obtain it)

- Full LessIsMore-FSE2025 `filter_train.csv` (~850 MB): see the original
  paper's replication package (https://arxiv.org/abs/2502.14212).
- Filter 3 fine-tuned checkpoint (~1 GB): released separately on
  Hugging Face / ModelScope; see `skills/cleantest-coverage-filter/references/model-card.md`.
- Per-sample inference dump `test_pred_a800.csv` (50 MB): regenerable
  from the checkpoint; or available on Zenodo with DOI (planned).

## Citation

If you use this codebase, please cite both the original paper and this
implementation:

```bibtex
@inproceedings{zhang2025cleantest,
  title     = {Less is More: On the Importance of Data Quality for Unit Test Generation},
  author    = {Zhang, Junwei and Hu, Xing and Gao, Shan and Xia, Xin and Lo, David and Li, Shanping},
  booktitle = {Proceedings of the 33rd ACM International Conference on the Foundations of Software Engineering},
  year      = {2025}
}

@misc{yang2026cleantestagent,
  title  = {{CleanTest-Agent}: A Multi-Agent Skill-Orchestrated System for Unit Test Training Data Quality},
  author = {Yang, Yong},
  year   = {2026},
  howpublished = {\url{https://github.com/<user>/cleantest-agent}}
}
```

## License

MIT (see [LICENSE](LICENSE)). The bundled
`data/sample_5000.csv` is a derivative subset of Microsoft's MIT-licensed
Methods2Test, redistributed under the same terms.
```

---

## 5. After the first public push

These are nice-to-haves, not blockers:

- **Add a CITATION.cff** at the repo root so GitHub renders a "Cite this
  repository" widget.
- **Enable Dependabot** (Settings → Code security → Dependabot alerts).
- **Add a CONTRIBUTING.md** if you plan to accept PRs.
- **Add a CODE_OF_CONDUCT.md** (Contributor Covenant).
- **Set the social preview image** (Settings → Social preview) to a
  screenshot of the pipeline architecture diagram from §6 of the paper.
- **Add an issue template** for bug reports and skill suggestions
  (`.github/ISSUE_TEMPLATE/`).

---

## 6. What to NOT do

- **Do not** push the parent directory `期末大作业/` --- only push the
  inner `cleantest-agent/` directory.
- **Do not** include the course-platform submission zip
  (`cleantest-agent-v*.zip`); the repo IS the canonical source.
- **Do not** commit the LessIsMore-FSE2025 full `filter_train.csv` even
  if you have it locally; redistribute by reference only.
- **Do not** force-push to `main` once others have cloned --- if you
  must rewrite history (e.g. to scrub a leaked secret), open an issue
  before doing it.
