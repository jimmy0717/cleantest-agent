---
name: cleantest-syntax-filter
description: >
  Detects and removes syntactic noise from unit test training data using
  tree-sitter AST parsing with optional LLM enhancement for borderline cases.
  Covers 7 noise types from the CleanTest framework (FSE 2025).
  Triggers: "check syntax noise", "detect noisy test syntax",
  "filter syntax errors", "检测语法噪声"
---

# Syntax Noise Filter

This skill detects 7 types of syntactic noise in Java unit test training data.

## Noise Types

| ID | Type | Detection Method | LLM Enhanced |
|----|------|-----------------|:------------:|
| N1 | Syntax Errors | tree-sitter ERROR node | ✅ Confirm if code is truly broken |
| N2 | Empty Exception | catch/finally with empty block | — |
| N3 | Empty Method | method body < 3 children | ✅ Check if trivial test is valid |
| N4 | Ambiguous Type | generics without `extends` | — |
| N5 | Unnecessary Annotations | Aho-Corasick automaton (21,954 patterns) | — |
| N6 | Non-English Literals | regex for CJK characters | — |
| N7 | Synchronized Keywords | keyword match | — |

## Usage

```bash
python skills/cleantest-syntax-filter/scripts/syntax_filter.py \
  --input_csv <path> \
  --output_csv <path> \
  [--llm_enhance]
```

## Example

**Input** (focal method):
```java
@GetMapping("/api/users")
public List<User> getUsers() { return repo.findAll(); }
```
**Output**: `NOISE (unnecessary_annotations)` — matched via Aho-Corasick.

## LLM Enhancement Protocol

For noise types N1 and N3, when the rule-based detector flags a sample,
the LLM is asked to confirm:

```
You are a Java test quality expert. The following code was flagged by
static analysis as [{noise_type}]:

```java
{code_snippet}
```

Static analysis result: {rule_result}

Is this truly a defective/noisy test that should be removed from training data?
Answer ONLY with:
- "NOISE: <one-line reason>" (confirm removal)
- "KEEP: <one-line reason>" (override, this is valid code)
```

Only ~5% of samples typically require LLM confirmation.

## Scripts

- `scripts/syntax_filter.py` — Main filter logic
- `references/noise_rules.md` — Detailed noise type documentation
