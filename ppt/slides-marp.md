---
marp: true
theme: default
paginate: true
size: 16:9
header: 'CleanTest-Agent  ·  BUAA SE 2026 Final Project'
footer: 'Yong Yang  ·  yang_qhd@buaa.edu.cn  ·  github.com/jimmy0717/cleantest-agent'
style: |
  /* Tight typography for an info-dense 3-minute talk. */
  section {
    font-size: 21px;
    padding: 50px 60px 60px 60px;
    color: #111;
    background: #ffffff;
  }
  section.lead {
    text-align: center;
    background: linear-gradient(135deg, #fafafa 0%, #f0f4f8 100%);
  }
  section.lead h1 {
    font-size: 46px;
    margin-bottom: 8px;
    color: #1a3a5c;
  }
  section.lead h2 {
    font-size: 28px;
    color: #2563eb;
    font-weight: 500;
    margin-top: 0;
  }
  section.lead h3 {
    font-size: 18px;
    color: #555;
    font-weight: 400;
    margin-top: 30px;
  }
  h1 { font-size: 30px; color: #1a3a5c; margin-bottom: 6px; border-bottom: 2px solid #2563eb; padding-bottom: 4px; }
  h2 { font-size: 22px; color: #1a3a5c; margin-top: 14px; margin-bottom: 8px; }
  h3 { font-size: 19px; color: #2563eb; margin-top: 12px; margin-bottom: 6px; }
  ul, ol { margin: 4px 0 8px 24px; }
  li { margin: 2px 0; line-height: 1.4; }
  p { margin: 6px 0; line-height: 1.45; }
  table {
    font-size: 18px;
    border-collapse: collapse;
    margin: 8px 0;
    width: 100%;
  }
  th, td { border: 1px solid #d1d5db; padding: 5px 9px; text-align: left; }
  th { background: #eef2f7; font-weight: 600; color: #1a3a5c; }
  tr:nth-child(even) td { background: #fafafa; }
  code { background: #f1f5f9; padding: 1px 5px; border-radius: 3px; font-size: 0.92em; color: #1d4ed8; }
  pre {
    background: #1e293b;
    color: #e2e8f0;
    padding: 10px 14px;
    border-radius: 4px;
    font-size: 16px;
    line-height: 1.4;
    overflow-x: auto;
  }
  pre code { background: transparent; color: inherit; padding: 0; }
  blockquote {
    border-left: 4px solid #2563eb;
    background: #eff6ff;
    padding: 8px 14px;
    margin: 10px 0;
    color: #1e3a8a;
    font-style: italic;
  }
  strong { color: #b91c1c; }
  header { font-size: 13px; color: #6b7280; }
  footer { font-size: 12px; color: #6b7280; }
  section::after {
    font-size: 13px;
    color: #6b7280;
  }
  /* Two-column layout helper. Use:
     <div class="cols"><div>left</div><div>right</div></div> */
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  /* Subtle highlight box. */
  .box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #2563eb;
    padding: 8px 12px;
    margin: 6px 0;
    border-radius: 3px;
    font-size: 19px;
  }
---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _header: '' -->
<!-- _footer: '' -->

# CleanTest-Agent

## A Multi-Agent Skill-Orchestrated System for Unit Test Training Data Quality Assurance

### Yong Yang  ·  School of Software, Beihang University
### yang_qhd@buaa.edu.cn
### Software Requirements Analysis & System Design  ·  Final Project

---

# Problem & Motivation

## 43.52% of Methods2Test Training Data is Noise

<div class="cols">
<div>

- Methods2Test: 780,944 test cases from 91,385 open-source Java projects.
- 43.52% contain noise (Zhang et al., **FSE 2025 Distinguished Paper**).
- Filtering this noise improves downstream branch coverage by an average of 67% on the Defects4J benchmark.

</div>
<div>

**Noise distribution (8 types, Methods2Test)**

| Type | % |
|---|---:|
| Unnecessary annotations | **41.64%** |
| No relevance | 12.70% |
| Low coverage | 3.95% |
| Ambiguous data type | 3.08% |
| Syntax errors | 1.11% |
| Empty exception handling | 0.68% |
| Missing implementation | 0.34% |
| Non-English literals | 0.16% |

</div>
</div>

<div class="box">

**Problems with the original CleanTest:** monolithic Python scripts, no test suite, not invokable from AI coding assistants, naïve dictionary matching takes ~30 min on 600 K samples.

</div>

---

# System Architecture: Pipeline-of-Skills

```
                User / Coding Assistant  (natural language)
                                |
                                v
                Orchestrator Skill  (cleantest-pipeline)
                |               |               |
                v               v               v
            Filter 1         Filter 2         Filter 3
            Syntax           Relevance        Coverage
            AST +            Name match       Label scan (default) /
            Aho-Corasick     + LLM            Qwen2.5-Coder-0.5B
                             fallback         (model mode)
                |               |               |
                +---------------+---------------+
                                v
                    Clean Dataset + Noise Report
```

- **4 composable Agent Skills** sharing the SKILL.md protocol — drop into CodeBuddy, Claude Code, or Cursor with one natural-language trigger.
- **Filter 3 ships two modes:** deterministic label-mode row scan over JaCoCo `condition_cover_rate` (default; no model, no GPU); **model mode** falls back to a fine-tuned Qwen2.5-Coder-0.5B regression checkpoint when JaCoCo labels are unavailable.
- Each filter is independently testable and extensible (36-case pytest suite).

---

# Model-Driven Approach: Right Tool for the Right Subtask

|              | **Rules** (deterministic) | **ML model** (learned) | **LLM** (semantic) |
|--------------|---------------------------|------------------------|--------------------|
| What         | AST + Aho-Corasick over a 21,954-pattern dictionary | Filter 3: JaCoCo label scan (default) **or** Qwen2.5-Coder-0.5B fine-tuned on 469 K rows | DeepSeek-V4-Flash |
| Coverage     | 87.3% of samples decided here | $O(N)$ row scan in label mode | Borderline ~12.7% only |
| Time / sample | ~0.2 ms | ~0 (label mode) | ~3 s (API) |
| $$ Cost      | 0 | 0 (label mode) | ~$4.5 / 593 K samples |

<div class="box">

**vs. pure LLM:** rules handle 87.3% of samples free and instantly; the LLM is invoked **only on the 12.7% it actually adds value to** — and never on the 21,954-pattern annotation dictionary it cannot memorise.

</div>

**Five design patterns applied:** Strategy (filter selection)  ·  Pipeline (sequential stages)  ·  Facade (LLM-client abstraction)  ·  Observer (`NoiseReport` accumulator)  ·  Reflection (Filter 2 self-correction).

---

# Highlight 1 — Reflection Mechanism (Filter 2, opt-in)

## A 5-Rule Structured Self-Check on Borderline LLM Verdicts

Inspired by the **Lab 1 Reflection Agent** pattern. Triggered when the initial LLM verdict is `IRRELEVANT`; the LLM re-decides against an explicit checklist drawn from the software-testing literature:

| # | Rule | Source |
|---|------|--------|
| R1 | Call Graph (depth ≤ 2 chain into focal method) | Tufano et al. 2022 (extended) |
| R2 | State Verification (focal-only state assertion) | Meszaros 2007 |
| R3 | Behavior Verification (`verify()`, mocks, listeners) | Meszaros 2007 |
| R4 | Naming Equivalence (save/persist, get/fetch, ...) | this work |
| R5 | Counterfactual (would the test still pass if the focal method were deleted?) | this work |

<div class="box">

**Validation on 45 zero-overlap samples (manual ground truth):** 7 verdicts changed (15.6%); **5 rescued from false removal (11.1% rescue rate)**; 6/7 changes verified correct on manual inspection (**85.7% reflection accuracy**).

Default: **off**. The headline F1 = 0.965 reported on the next slides does **not** include reflection; the rescue is an additive contribution on top.

</div>

---

# Key Optimization — Aho-Corasick

## ~11.5× Pipeline Speedup, Filtering Result Unchanged

|                     | Naïve | **Aho-Corasick** |
|---------------------|-------|------------------|
| Complexity          | $O(N \cdot K \cdot L)$ | $O(N \cdot (L + Z))$ |
| K = 21,954 patterns | scan all patterns per sample | single automaton pass |
| Filter 1 alone (593,953 samples) | ~30 min | ~1.6 min  (~18.8×) |
| Whole pipeline                   | ~31 min | ~2.6 min  (~11.5×) |
| Filtering result    | 53.97% removed | **53.97% removed (identical)** |

<div class="box">

A classic algorithmic optimisation, applied at exactly the bottleneck the LLM cannot fix. Pure performance — correctness unchanged.

</div>

---

# Experiment Design — 4 Research Questions

- **RQ1.** Does CleanTest-Agent reproduce the original CleanTest detection?  →  Yes (annotation noise: 43.68% vs. 41.64%).
- **RQ2.** Model-driven vs. pure LLM?  →  Real DeepSeek-V4-Flash experiment.
- **RQ3.** Aho-Corasick speedup?  →  ~11.5× (whole pipeline) confirmed.
- **RQ4.** Cost & speed comparison?  →  Rules ~13,000 – 15,000× faster than LLM.

## Experiment setup (real API + real GPU, no simulation)

<div class="cols">
<div>

**LLM baselines (RQ2 / RQ4)**
- Provider: DeepSeek-V4-Flash via Tencent Cloud TokenHub
- Dataset: 500 stratified samples from Methods2Test (231 noise / 269 clean)
- Temperature: 0.0 (deterministic, reproducible)
- Total real API calls: 1,000  (500 zero-shot + 500 few-shot)

</div>
<div>

**Filter 3 model mode (highlight 2)**
- Base model: Qwen2.5-Coder-0.5B (Apache 2.0)
- Training data: `filter_train.csv` (469,174 rows; 80/10/10 stratified split)
- Hardware: single A800-SXM4-80 GB, bf16, batch 64, max_seq 512, lr 3e-5 cosine, 2 epochs (~3.32 h)
- Held-out test set: 46,921 samples

</div>
</div>

---

# Results — Rules + Selective LLM ≫ Pure LLM

| Method            | Precision | Recall | **F1** | Time (500 samples) |
|-------------------|:---------:|:------:|:------:|:------------------:|
| Rule-based        | 1.000     | 1.000  | **1.000** | **0.11 s**     |
| LLM zero-shot     | 0.505     | 0.221  | 0.307  | 1,487 s            |
| LLM few-shot      | 0.534     | 0.303  | 0.387  | 1,642 s            |
| **Hybrid (ours)** | **0.974** | **0.956** | **0.965** | **< 60 s**  |

<div class="cols">
<div>

**Quality**
- F1: **0.965 vs. 0.387** (~+149%)
- LLM zero-shot misses ~77.9% of noise; **87.8% of those misses are unnecessary-annotations** — the failure mode the rule-based filter catches deterministically.

</div>
<div>

**Speed & cost**
- Rules: 0.11 s vs. LLM 1,642 s on 500 samples — **~13,000–15,000× faster**.
- Cost on 593,953 samples: **~$4.5** (hybrid) vs. ~$35–58 (single-LLM-per-sample).

</div>
</div>

<div class="box">

**Root cause**: the LLM cannot memorise the 21,954-pattern annotation dictionary that drives 41.64% of the noise. Rules can, deterministically, in microseconds.

</div>

---

# Why Pure LLM Falls Short — A Real Sample

<div class="cols">
<div>

```java
@PostMapping(path = "/account/new")
public ResponseEntity<?> createAccount(
    @Valid @RequestBody
    final AccountDto account, ...) {
    ...
}
```

**A real Methods2Test sample, drawn from our 500-sample evaluation set.**

</div>
<div>

|              | Rule-based | LLM (DeepSeek-V4-Flash) |
|--------------|:----------:|:-----------------------:|
| Verdict      | **NOISE**  | **CLEAN** (incorrect)   |
| Reason       | Aho-Corasick matches `@PostMapping` against the 21,954-pattern dictionary | "looks like a valid Spring controller" |
| Time         | < 0.01 ms  | ~3,000 ms               |
| Cost         | 0          | API token               |

</div>
</div>

<div class="box">

**Root cause**: the LLM evaluates code *quality*, not *training-data suitability*. Knowing that `@PostMapping` is "unnecessary for the test-generation training task" requires the full 21,954-pattern dictionary in context — physically impossible in a single prompt window.

</div>

---

# Highlight 2 — Filter 3 Model Mode Replaces CodeGPT

## Fine-Tuned Qwen2.5-Coder-0.5B beats the Original Paper's CodeGPT

| Metric on 46,921-sample held-out test split | **This work** (Qwen 0.5B) | CodeGPT (Zhang et al., FSE 2025) |
|----------------------------------------------|---------------------------:|---------------------------------:|
| MAE                                          | **0.0309** | 0.0798  (~2.6× higher) |
| MSE                                          | **0.0039** | 0.0105  (~2.7× higher) |
| RMSE                                         | **0.0628** | — |
| R²                                           | **0.604**  | — |
| Pearson r / Spearman ρ                       | **0.778 / 0.848** | — |
| F1 @ τ = 0.10                                | **0.857**  | — |
| F1 @ τ = 0.15                                | **0.912**  | — |

<div class="box">

**Why it matters.** Filter 3 originally needed JaCoCo coverage labels — unavailable in most real datasets. The fine-tuned regressor lets Filter 3 run **label-free** with held-out **MAE 0.0309**, removing the original CleanTest pipeline's hardest dependency. ~3.32 h training on a single A800 80 GB.

</div>

---

# Software Engineering Practices

<div class="cols">
<div>

## Requirements & Design

- 3 use cases  ·  9 functional + 6 non-functional requirements  ·  full traceability matrix.
- UML use-case / activity / sequence diagrams.
- Component diagram, class diagram.
- **5 design patterns**: Strategy / Pipeline / Facade / Observer / Reflection.

## Course-lab method integration

- Lab 1 Reflection pattern  →  Filter 2 self-correction step.
- Lab 2 DSL validation       →  "rule-first, LLM only on residual" topology.
- Lab 3 formal verification  →  AST structural checking + dictionary completeness.

</div>
<div>

## Testing & CI / CD

- **36 pytest cases**, 100% passing.
- pytest + flake8 + mypy quality gate.
- **CI**: GitHub Actions matrix on Python 3.10 / 3.11 / 3.12.
- **CD** (`publish.yml`, tag-driven):
  build  →  `twine check --strict`  →  PyPI publish via **OIDC Trusted Publisher** (no API token)  →  **sigstore** keyless signing  →  attach signed wheel + sdist to the GitHub Release.
- **Result**: `pip install cleantest-agent` lands v0.1.1 on every Python ≥ 3.10 environment, signature-verifiable offline.

</div>
</div>

---

# Conclusion — Four Contributions

1. **Skill-based architecture** — 4 composable Agent Skills via the SKILL.md protocol; natural-language trigger from CodeBuddy / Claude Code / Cursor.
2. **Hybrid rule + selective-LLM detection** — **F1 = 0.965 vs. pure-LLM 0.387** on real DeepSeek-V4-Flash experiments; ~13,000-15,000× faster.
3. **Aho-Corasick optimisation** — ~11.5× pipeline speedup (~18.8× on Filter 1 alone), filtering result identical.
4. **Two methodological enhancements over the original CleanTest:**
    - **Reflection** (Filter 2, opt-in) — 5-rule structured self-check rescues 5/45 (11.1%) borderline samples with 85.7% accuracy.
    - **Filter 3 model mode** — fine-tuned Qwen2.5-Coder-0.5B replaces the CodeGPT backbone with held-out **MAE 0.0309** (~2.6× lower).

> **Systematic software design beats "just ask the LLM" — supported by real-API experiments and a reproducible CI / CD pipeline.**

<div class="box">

Released as **v0.1.1 on PyPI**:  `pip install cleantest-agent`
GitHub Actions matrix green; sigstore-signed wheel attached to the v0.1.1 GitHub Release.

</div>

---

<!-- _class: lead -->
<!-- _paginate: false -->
<!-- _header: '' -->
<!-- _footer: '' -->

# Thank you

## Questions?

### GitHub  ·  https://github.com/jimmy0717/cleantest-agent
### PyPI    ·  https://pypi.org/project/cleantest-agent/
### Contact ·  yang_qhd@buaa.edu.cn
