---
name: cleantest-relevance-filter
description: >
  Determines whether a unit test is relevant to its focal method using
  AST-based method name matching with LLM fallback for semantic judgment.
  Triggers: "check test relevance", "filter irrelevant tests",
  "test-focal method relevance", "检查测试相关性"
---

# Relevance Filter

This skill assesses whether a unit test actually tests its paired focal method.

## Two-Stage Detection

### Stage A: AST Name Matching (Fast Path)
1. Parse focal method → extract method name + parameter count
2. Parse test case → extract all method invocations + argument counts
3. Compute intersection of (name, param_count) tuples
4. If intersection > 0 → **RELEVANT** (pass immediately)
5. If intersection == 0 → proceed to Stage B

### Stage B: LLM Semantic Judgment (Borderline Cases Only)
Only invoked for samples where Stage A found zero name matches (~12.7% of data).

```
Given the following focal method and test case:

Focal method:
```java
{src_fm}
```

Test case:
```java
{target}
```

The test does NOT directly invoke any method matching the focal method name.
However, it might test the focal method indirectly via:
- Wrapper methods
- Inheritance / method overriding
- Aliases or helper methods
- Testing side effects of the focal method

Is this test case semantically relevant to the focal method?
Answer ONLY with:
- "RELEVANT: <one-line explanation>"
- "IRRELEVANT: <one-line explanation>"
```

## Usage

```bash
python -m skills.cleantest-relevance-filter.scripts.relevance_filter \
  --input_csv <path> \
  --output_csv <path> \
  [--llm_enhance]
```

## Scripts

- `scripts/relevance_filter.py` — Main filter logic
- `scripts/llm_relevance.py` — LLM fallback client
