<!--
Thanks for opening a PR. The few asks below help us review faster.
Delete sections that genuinely do not apply.
-->

## What this changes

<!-- One paragraph. What is the user-visible difference after this PR
     lands? -->

## Why

<!-- Optional: a sentence or two on the motivation, especially if the
     change is not obviously aligned with the four project goals listed
     in CONTRIBUTING.md . -->

## Test plan

<!-- The convention is "test first": link the commit that adds a failing
     test, and then describe the fix. If the change is documentation
     only or otherwise untestable, write "no test (doc only)". -->

- [ ] Failing test added in commit: <!-- abc1234 -->
- [ ] `make lint` passes locally
- [ ] `make test` passes locally

## Scope check

- [ ] This change keeps the rule-based path deterministic and free.
- [ ] This change does not require calling the LLM on every sample.
- [ ] No new runtime dependency was added without prior discussion.

## Linked issue

<!-- Closes #123  -->
