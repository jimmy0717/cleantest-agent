"""LLM client for enhanced noise detection (OpenAI-compatible API)."""

import os
from typing import Literal

from openai import OpenAI

# Default to environment variable; user can override
_client = None


def get_client() -> OpenAI:
    """Lazy-initialize and return the OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )
    return _client


def llm_confirm_syntax_noise(
    code: str,
    noise_type: str,
    rule_result: str,
    model: str = "gpt-4o-mini",
) -> Literal["NOISE", "KEEP"]:
    """Ask LLM to confirm whether a syntax-flagged sample is truly noisy.

    Returns "NOISE" or "KEEP".
    """
    prompt = f"""You are a Java test quality expert. The following code was flagged \
by static analysis as [{noise_type}]:

```java
{code}
```

Static analysis result: {rule_result}

Is this truly a defective/noisy test that should be removed from training data?
Answer ONLY with one of:
- "NOISE: <one-line reason>"
- "KEEP: <one-line reason>"
"""
    client = get_client()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0.0,
    )
    answer = resp.choices[0].message.content.strip()
    return "KEEP" if answer.upper().startswith("KEEP") else "NOISE"


def llm_judge_relevance(
    src_fm: str,
    target: str,
    model: str = "gpt-4o-mini",
) -> Literal["RELEVANT", "IRRELEVANT"]:
    """Ask LLM to judge semantic relevance between focal method and test.

    Only called when AST name matching finds zero intersection.
    Returns "RELEVANT" or "IRRELEVANT".
    """
    prompt = f"""Given the following focal method and test case:

Focal method:
```java
{src_fm}
```

Test case:
```java
{target}
```

The test does NOT directly invoke any method matching the focal method name.
However, it might test the focal method indirectly via wrappers, inheritance,
aliases, or side effects.

Is this test case semantically relevant to the focal method?
Answer ONLY with one of:
- "RELEVANT: <one-line explanation>"
- "IRRELEVANT: <one-line explanation>"
"""
    client = get_client()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0.0,
    )
    answer = resp.choices[0].message.content.strip()
    return "RELEVANT" if answer.upper().startswith("RELEVANT") else "IRRELEVANT"
