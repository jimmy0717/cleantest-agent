---
name: cleantest-relevance-filter
description: >
  Determines whether a unit test is relevant to its focal method using
  AST-based method name matching with LLM fallback for semantic judgment.
  Triggers: "check test relevance", "filter irrelevant tests",
  "test-focal method relevance", "检查测试相关性"
---

# Relevance Filter

## Prerequisites

This skill depends on the open-source [`cleantest-agent`](https://github.com/jimmy0717/cleantest-agent) Python package:

```bash
pip install cleantest-agent
# or, from a checkout of the project repository:
pip install -e .
```

For Stage B (LLM semantic judgement) you also need an OpenAI-compatible
endpoint. Set:

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.deepseek.com/v1"   # any compatible endpoint works
```

This skill assesses whether a unit test actually tests its paired focal method.

## Two-Stage Detection

### Stage A: AST Signature Matching (Fast Path)
1. Parse focal method → extract method name + parameter count + parameter types
2. Parse test case → extract all method invocations + argument counts + argument types
3. Check if at least one function call in the test matches the focal method in name, number of parameters, and parameter types
4. If match found → **RELEVANT** (pass immediately)
5. If no match → proceed to Stage B

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
# Batch mode
python skills/cleantest-relevance-filter/scripts/relevance_filter.py \
  --input_csv <path> \
  --output_csv <path> \
  [--llm_enhance]

# Single sample (LLM judgment)
python skills/cleantest-relevance-filter/scripts/llm_relevance.py \
  --src_fm "public void save(String d) { db.insert(d); }" \
  --target "@Test public void testLen() { assertEquals(5, \"hello\".length()); }"
```

## Example

**Input**: focal = `save(String)`, test = `testLen()` (calls `length()`, not `save`)
**Stage A**: methods={("save",1)}, invocations={("assertEquals",2),("length",0)} → overlap=0
**Stage B (LLM)**: "IRRELEVANT: test checks String.length(), unrelated to save()"
**Output**: `NOISE (no_relevance)`

## Scripts

- `scripts/relevance_filter.py` — Main filter logic
- `scripts/llm_relevance.py` — LLM fallback client
