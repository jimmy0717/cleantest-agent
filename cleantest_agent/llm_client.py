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
    answer = (resp.choices[0].message.content or "").strip()
    return "KEEP" if answer.upper().startswith("KEEP") else "NOISE"


def llm_judge_relevance(
    src_fm: str,
    target: str,
    model: str = "gpt-4o-mini",
    reflection: bool = False,
) -> Literal["RELEVANT", "IRRELEVANT"]:
    """Ask LLM to judge semantic relevance between focal method and test.

    Only called when AST name matching finds zero intersection.
    If reflection=True, applies a self-reflection step when initial judgment
    is IRRELEVANT, giving the LLM a chance to reconsider indirect testing.
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
    initial_answer = (resp.choices[0].message.content or "").strip()
    initial_verdict: Literal["RELEVANT", "IRRELEVANT"] = (
        "RELEVANT" if initial_answer.upper().startswith("RELEVANT") else "IRRELEVANT"
    )

    # Reflection: only when initial judgment is IRRELEVANT (reduce false removals)
    if reflection and initial_verdict == "IRRELEVANT":
        reflection_prompt = f"""You previously judged this test-focal pair as IRRELEVANT:

Your initial answer: {initial_answer}

Now apply the following checklist (based on software testing literature):

Rule 1 (Call Graph, extended from Tufano et al. 2022): Does the test call any method
that INTERNALLY calls the focal method? Look for delegation, forwarding,
wrapper, or orchestration patterns (depth <= 2 call chain).
→ If YES: revise to RELEVANT

Rule 2 (State Verification, Meszaros 2007): Does the test assert on state
that could ONLY have been produced by the focal method? (e.g., database
record count, collection size, configuration value, file content)
→ If YES: revise to RELEVANT

Rule 3 (Behavior Verification, Meszaros 2007): Does the test use verify(),
mock interactions, or event listeners that would be triggered by the focal method?
→ If YES: revise to RELEVANT

Rule 4 (Naming Equivalence): Are the test method name and focal method name
semantic synonyms? (save/persist, delete/remove, get/fetch, init/setup,
execute/run, authenticate/login)
→ If YES: revise to RELEVANT

Rule 5 (Counterfactual test): If the focal method were DELETED
from the codebase, would this test still pass unchanged?
→ If NO (test would fail): revise to RELEVANT

If NONE of the 5 rules apply: confirm IRRELEVANT.

Answer ONLY with one of:
- "RELEVANT: <rule number and one-line explanation>"
- "IRRELEVANT: confirmed, none of the 5 rules apply"
"""
        resp2 = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": reflection_prompt}],
            max_tokens=80,
            temperature=0.0,
        )
        final_answer = (resp2.choices[0].message.content or "").strip()
        return "RELEVANT" if final_answer.upper().startswith("RELEVANT") else "IRRELEVANT"

    return initial_verdict
