---
name: cleantest-syntax-filter
description: >
  Detects and removes syntactic noise from unit test training data using
  tree-sitter AST parsing with optional LLM enhancement for borderline cases.
  Covers 6 noise types from the CleanTest framework (FSE 2025).
  Triggers: "check syntax noise", "detect noisy test syntax",
  "filter syntax errors", "检测语法噪声"
---

# Syntax Noise Filter

## Prerequisites

This skill depends on the open-source [`cleantest-agent`](https://github.com/jimmy0717/cleantest-agent) Python package:

```bash
pip install cleantest-agent
# or, from a checkout of the project repository:
pip install -e .
```

The 21,954-pattern annotation dictionary is shipped as package data
(`cleantest_agent/data/noise_modifier_fm.txt`), so the filter works even when
this skill is installed in isolation in `~/.codebuddy/skills/` /
`~/.claude/skills/` etc.

This skill detects 6 types of syntactic noise in Java unit test training data,
corresponding to the original CleanTest paper's syntax filter.

## Noise Types

| ID | Type | Detection Method | LLM Enhanced |
|----|------|-----------------|:------------:|
| N1 | Syntax Errors | tree-sitter ERROR node | Yes (confirm if code is truly broken) |
| N2 | Empty Exception Handling | catch/finally with empty block | -- |
| N3 | Missing Implementation | method body < 3 children | Yes (check if trivial test is valid) |
| N4 | Ambiguous Data Type | generics markers (`<E>`, `<T>`, `<?>`, etc.) | -- |
| N5 | Unnecessary Annotations | Aho-Corasick automaton (21,954 patterns) | -- |
| N6 | Non-English Literals | regex for CJK characters | -- |

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
**Output**: `NOISE (unnecessary_annotations)` -- matched via Aho-Corasick.

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

- `scripts/syntax_filter.py` -- Main filter logic
- `references/noise_rules.md` -- Detailed noise type documentation
