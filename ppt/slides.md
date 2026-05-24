# Slide 1: Title

## CleanTest-Agent
### A Multi-Agent Skill-Orchestrated System for Unit Test Training Data Quality Assurance

Yong Yang -- School of Software, Beihang University
yang_qhd@buaa.edu.cn

Software Requirements Analysis & System Design -- Final Project

---

# Slide 2: Problem & Motivation

## 43.52% of Methods2Test Training Data is Noise

- Methods2Test dataset: 780,944 test cases from 91,385 projects.
- 43.52% contain noise (Zhang et al., FSE 2025 Distinguished Paper).
- 8 noise types in the original taxonomy (Table 5 of the paper):
  unnecessary annotations (41.64%), no relevance (12.70%),
  low coverage (3.95%), ambiguous data types (3.08%),
  syntax errors (1.11%), empty exception handling (0.68%),
  missing implementation (0.34%), non-English literals (0.16%).
- Filtering this noise improves downstream branch coverage by an
  average of 67% on Methods2Test (Defects4J benchmark).

## Challenges with the Original CleanTest

- Implemented as monolithic Python scripts; no test suite, no
  reusability.
- Cannot be directly invoked by modern AI coding assistants.
- Linear annotation matching is slow (~30 min for 600 K samples).

---

# Slide 3: System Architecture

## CleanTest-Agent: Pipeline-of-Skills

```
User / Coding Assistant (natural language)
                |
                v
   Orchestrator Skill (cleantest-pipeline)
        |          |          |
        v          v          v
   Filter 1   Filter 2    Filter 3
   Syntax     Relevance   Coverage
   AST +      NameMatch   label scan (default) /
   Aho-       + LLM       Qwen2.5-Coder-0.5B
   Corasick   fallback    (model mode)
        |          |          |
        +----------+----------+
                   v
        Clean Dataset + Noise Report
```

- 4 composable Agent Skills following the SKILL.md protocol.
- Filter 3 ships **two modes**: a deterministic label-mode row scan
  over JaCoCo `condition_cover_rate` (default; no model, no GPU),
  and a **model mode** that delegates to a fine-tuned
  Qwen2.5-Coder-0.5B regression checkpoint when no ground-truth
  labels are available.
- Compatible with CodeBuddy, Claude Code, and Cursor.
- Each filter is independently testable and extensible.

---

# Slide 4: Model-Driven Approach

## Right Tool for the Right Subtask

| Rules (deterministic) | ML model (learned) | LLM (semantic) |
|---|---|---|
| AST parsing, Aho-Corasick | Filter 3 label-mode scan over JaCoCo labels (default); Qwen2.5-Coder-0.5B regression model fine-tuned on 469K samples for label-free settings | DeepSeek-V4-Flash |
| 21,954 patterns, 100% recall | $O(N)$ row scan for label mode | Borderline cases only (~12.7%) |
| $0 cost, ~0.2 ms / sample | $0 cost in label mode | API call, ~3 s / sample |

vs. pure LLM: rules handle 87.3% (free, instant); LLM handles only the
12.7% where it adds value.

### Reflection mechanism (Filter 2, opt-in)

- Inspired by the Lab 1 Reflection Agent pattern.
- Implemented as opt-in `--reflection` flag (default off, so the
  headline F1 = 0.965 below does **not** include reflection).
- When enabled and the LLM's initial verdict is IRRELEVANT, a
  structured self-reflection step applies a 5-rule checklist
  drawn from the software-testing literature: Call Graph
  (extended from Tufano 2022), State Verification (Meszaros 2007),
  Behavior Verification (Meszaros 2007), Naming Equivalence,
  Counterfactual.
- Validation on 45 zero-overlap samples: 7 verdicts changed (15.6%
  change rate); 5 rescued from false removal (11.1% rescue rate);
  6 / 7 changes verified correct by manual inspection (85.7% accuracy).

### Design patterns applied

- Strategy (filter selection)
- Pipeline (sequential stages)
- Facade (LLM-client abstraction)
- Observer (NoiseReport accumulator)
- Reflection (self-correction for borderline cases)

---

# Slide 5: Key Optimization -- Aho-Corasick

## ~11.5× Pipeline Speedup

| | Naïve | Aho-Corasick |
|---|---|---|
| Complexity | O(N · K · L) | O(N · (L + Z)) |
| K = 21,954 patterns | scan all patterns per sample | single automaton pass |
| Time (600 K samples) | ~30 min | ~2.6 min |
| Filtering result | 53.97% removed | 53.97% removed (identical) |

Pure performance optimization -- correctness unchanged.

---

# Slide 6: Experiment Design

## 4 Research Questions (real-API validation)

- RQ1: Does our system reproduce the original CleanTest results?
  → Yes (annotation noise: 43.68% vs. 41.64%).
- RQ2: Model-Driven vs. pure LLM? → Real DeepSeek-V4-Flash experiment.
- RQ3: Aho-Corasick speedup? → ~11.5× confirmed.
- RQ4: Speed comparison? → Rules are ~13,000–15,000× faster than LLM.

### Experiment setup

- LLM: DeepSeek-V4-Flash (Tencent Cloud TokenHub).
- Dataset: 500 stratified samples from Methods2Test.
- Temperature: 0.0 (deterministic, reproducible).
- Total API calls: 1,000 (500 zero-shot + 500 few-shot).

---

# Slide 7: Results (real experiment)

| Method | Precision | Recall | F1 | Time (500 samples) |
|---|---|---|---|---|
| Rule-based | 1.000 | 1.000 | 1.000 | 0.11 s |
| LLM zero-shot | 0.505 | 0.221 | 0.307 | 1,487 s |
| LLM few-shot | 0.534 | 0.303 | 0.387 | 1,642 s |
| Hybrid (ours) | 0.974 | 0.956 | 0.965 | < 60 s |

### Key numbers

- F1: 0.965 vs. 0.387 (~+149%).
- Speed: 0.11 s vs. 1,642 s (~13,000–15,000× faster).
- LLM zero-shot misses ~77.9% of noisy samples.
- Root cause: the LLM cannot memorize the 21,954-pattern annotation
  dictionary that drives the rule-based filter.

---

# Slide 8: Why Pure LLM Falls Short -- A Real Sample

```java
@PostMapping(path = "/account/new")
public ResponseEntity<?> createAccount(
    @Valid @RequestBody final AccountDto account, ...) {
    ...
}
```

| | Rule-based | LLM (DeepSeek-V4-Flash) |
|---|---|---|
| Verdict | NOISE | CLEAN |
| Reason | Aho-Corasick matches @PostMapping | "looks like a valid Spring controller" |
| Time | < 0.01 ms | ~3,000 ms |

Root cause: the LLM evaluates code *quality*, not training-data
*suitability*. Without the full 21,954-pattern dictionary in its
context, it cannot know that @PostMapping is "unnecessary for the
test-generation task".

---

# Slide 9: Software Engineering Practices

## Course Topics Applied

Requirements analysis:
- UML use-case, activity, and sequence diagrams.
- 9 functional + 6 non-functional requirements with a traceability matrix.

System design:
- Component diagram, class diagram.
- 5 design patterns: Strategy, Pipeline, Facade, Observer, Reflection.

Testing & CI/CD:
- 36 pytest test cases (Python 3.10 / 3.11 / 3.12 matrix on GitHub Actions).
- 100% of tests passing.
- Tag-driven CD pipeline (`publish.yml`): build -> twine check ->
  PyPI publish via OIDC Trusted Publisher (no API token) ->
  sigstore keyless signing -> attach signed wheel + sdist to the
  GitHub Release. Result: `pip install cleantest-agent` on PyPI.

Course-lab method integration:
- Lab 1 Reflection pattern → Filter 2 self-correction step.
- Lab 2 DSL validation → analogous to "rule-first, LLM only on residual".
- Lab 3 formal verification → analogous to AST structural checking.

---

# Slide 10: Conclusion

## Four Contributions

1. Skill-based architecture for test data cleaning (4 composable
   Agent Skills via the SKILL.md protocol).
2. Hybrid rule + LLM detection -- F1 = 0.965 vs. pure-LLM 0.387
   on real-API experiments.
3. Aho-Corasick optimization -- ~11.5× pipeline speedup
   (~18.8× on Filter 1 alone) without changing the filtering result.
4. Two methodological enhancements over the original CleanTest:
   (a) **Reflection** -- an opt-in 5-rule structured self-check for
   borderline relevance cases in Filter 2 (inspired by Lab 1,
   default off, additive on top of the headline F1 = 0.965),
   rescuing 5/45 (11.1%) borderline samples with 6/7 (85.7%)
   human-verified accuracy; (b) **Filter 3 model mode** -- fine-tuned
   Qwen2.5-Coder-0.5B on `filter_train.csv` (469 K rows,
   stratified 80/10/10) on a single A800 80 GB (~3.32 h),
   achieving held-out **MAE 0.0309 vs. CodeGPT 0.0798 (~2.6× lower)**
   and **F1 = 0.857 at τ = 0.10**; replaces the CodeGPT backbone of
   the original CleanTest paper.

## Core Message

> Systematic software design beats "just ask the LLM" -- supported by
> real-API experiments and a reproducible CI/CD pipeline.

Released as v0.1.1 on PyPI:
`pip install cleantest-agent`
(GitHub Actions matrix green; sigstore-signed wheel attached to the
v0.1.1 GitHub Release.)

---

Thank you. Questions?

GitHub : <https://github.com/jimmy0717/cleantest-agent>
PyPI   : <https://pypi.org/project/cleantest-agent/>
Contact: yang_qhd@buaa.edu.cn
