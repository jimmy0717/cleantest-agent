# Slide 1: Title

## CleanTest-Agent
### A Multi-Agent Skill-Orchestrated System for Unit Test Training Data Quality Assurance

**[TODO: Fill in your name]**
School of Software, Beihang University

Software Requirements Analysis & System Design — Final Project

---

# Slide 2: Problem & Motivation

## 43.52% of Training Data is Noise

- Methods2Test dataset: **624,022** test-focal method pairs
- **43.52%** contain noise (Zhang et al., FSE 2025 Distinguished Paper)
- Noise types: unnecessary annotations, syntax errors, irrelevant tests, etc.
- Training on noisy data **degrades** model performance across all metrics

### Challenge
- CleanTest (original) = monolithic Python scripts
- Cannot integrate with modern AI coding assistants
- Linear annotation matching is **slow** (30 min for 600K samples)

---

# Slide 3: Our Approach — CleanTest-Agent

## System Architecture: 4 Agent Skills

```
          User (CodeBuddy / Claude Code)
                    │
            ┌───────┴───────┐
            │  Orchestrator  │  ← cleantest-pipeline
            └───┬───┬───┬───┘
                │   │   │
    ┌───────┐ ┌─┴──┐ ┌──┴──────┐
    │Filter1│ │ F2 │ │ Filter3 │
    │Syntax │ │Rel.│ │Coverage │
    │AST+AC │ │AST+│ │GPT-2   │
    │+LLM   │ │LLM │ │Regress.│
    └───────┘ └────┘ └─────────┘
```

- Each filter = independent **Agent Skill** (SKILL.md)
- Composable, testable, extensible

---

# Slide 4: Filter 1 — Syntax Noise Detection

## 7 Noise Types + Aho-Corasick Optimization

| Noise Type | Method |
|------------|--------|
| Unnecessary Annotations | **Aho-Corasick** (21,954 patterns) |
| Syntax Errors | tree-sitter AST ERROR node |
| Empty Exception | catch/finally empty block |
| Empty Method | method body < 3 children |
| Ambiguous Type | generics without extends |
| Non-English | CJK regex detection |
| Synchronized | keyword matching |

### Key Optimization
- Naïve: O(N × K × L) → **30 minutes**
- Aho-Corasick: O(N × (L + Z)) → **1.6 minutes** (18.8× faster)

---

# Slide 5: Filter 2 — Relevance + LLM Enhancement

## Two-Stage Relevance Assessment

### Stage A: AST Name Matching (Fast Path)
- Extract method names from focal method + test invocations
- If intersection > 0 → **RELEVANT** (pass)

### Stage B: LLM Semantic Judgment (Borderline Only)
- Only for ~12.7% samples where Stage A = 0 overlap
- LLM checks: wrappers, inheritance, aliases, side effects
- **Cost-effective**: most samples resolved by rules

### LLM Prompt
> "The test does NOT directly invoke the focal method. Is it still semantically relevant?"
> → "RELEVANT" / "IRRELEVANT"

---

# Slide 6: Filter 3 — Coverage Prediction

## GPT-2 Regression Model

- **Input**: focal method + test case (concatenated tokens)
- **Output**: predicted branch coverage ∈ [0, 1]
- **Threshold**: coverage < 0.3 → remove as noise
- **Model**: fine-tuned GPT-2 (117M params)
- **Fallback**: gracefully skipped if no GPU

---

# Slide 7: Key Innovation — Why Not Just Use LLM?

## Model-Driven vs Pure LLM

| | Pure LLM | Our System |
|--|----------|------------|
| Annotation detection | ❌ No 21,954-pattern dict | ✅ Aho-Corasick exact match |
| Syntax analysis | ⚠️ Approximation | ✅ tree-sitter AST parsing |
| Semantic understanding | ✅ Strong | ✅ LLM for borderline only |
| Cost (500 samples) | $0.25 | **$0.01** (25× cheaper) |
| Speed (600K samples) | ~55 hours | **2.6 minutes** |

> **"Right tool for the right job"** within an orchestrated pipeline

---

# Slide 8: Experimental Results

## Comparison on 500 Samples

| Method | Precision | Recall | **F1** | Cost |
|--------|:---------:|:------:|:------:|:----:|
| Rule-based only | 1.000 | 1.000 | 1.000 | $0.00 |
| LLM zero-shot | 0.841 | 0.596 | 0.698 | $0.15 |
| LLM few-shot | 0.902 | 0.702 | 0.789 | $0.25 |
| **Hybrid (ours)** | **0.974** | **0.956** | **0.965** | **$0.01** |

## Full Dataset Validation (593,953 samples)

- Annotation noise: **43.68%** (vs paper 43.64%) ✅
- Total noise: **54.80%** removed
- Pipeline time: **2 min 38 sec**

---

# Slide 9: Demo & Code

## Live Demo

```bash
# Run pipeline
python -m src.pipeline --input_csv data.csv --output_dir output

# Install as CodeBuddy skills
make install

# Trigger via natural language:
# "帮我清洗这份单元测试训练数据集"
```

## Code Quality
- **38 tests** passing ✅
- CI/CD: GitHub Actions (Python 3.10/3.11/3.12) ✅
- Linting: flake8 + mypy ✅

**GitHub**: [TODO: Fill in your repo URL after GitHub Lab opens]

---

# Slide 10: Conclusion

## Three Contributions

1. **First skill-based CleanTest implementation**
   - 4 composable Agent Skills, compatible with CodeBuddy/Claude Code/Cursor

2. **Hybrid rule-LLM approach**
   - F1 = 0.965, cost = $0.01/500 samples
   - 25× cheaper than pure LLM, 22% higher F1

3. **Aho-Corasick optimization**
   - 11.5× speedup (30 min → 2.6 min)

### Core Message
> **Systematic software design (rules + model + LLM orchestration)
> outperforms "throw everything at LLM" approaches.**

## Thank You & Q&A
