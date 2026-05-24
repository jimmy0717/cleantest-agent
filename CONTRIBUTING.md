# Contributing to CleanTest-Agent

Thanks for taking the time to look at this. The goals of the project are
straightforward:

1. Stay faithful to the noise definitions in the original CleanTest paper
   (Zhang et al., FSE 2025).
2. Keep the rule-based path deterministic, fast, and free.
3. Touch the LLM only on borderline cases, and keep that touch optional.
4. Make every component drop into a coding-assistant workflow as a
   single SKILL.md skill.

If a contribution moves the project closer to those goals, it is in
scope. If it adds a dependency for a feature that does not, please open
an issue first so we can discuss.

## Development setup

```bash
git clone https://github.com/jimmy0717/cleantest-agent.git
cd cleantest-agent

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you push

```bash
make lint    # flake8 + mypy
make test    # the 36-case pytest suite
```

The CI matrix runs Python 3.10, 3.11, and 3.12; if `make test` passes
locally on any one of those, the CI matrix usually passes too.

## Filing an issue

Please use one of the templates under `.github/ISSUE_TEMPLATE/`. The
short version:

- Bug reports need a minimal CSV that reproduces the problem (5--10 rows
  is plenty), the exact `cleantest ...` command you ran, and the actual
  vs. expected output.
- Feature requests should describe the use case in 2--3 sentences and,
  if possible, sketch how it would look in `SKILL.md` form.
- Questions are also fine; use the `question` template.

## Pull requests

The convention is **test first**: write a failing test under `tests/`,
push that to a branch, confirm CI fails for the right reason, then push
the fix in a follow-up commit. The PR template asks you to link the
test commit explicitly so reviewers can do the same.

Small PRs (one logical change, < 200 LoC) are reviewed faster than
large ones. If you have a large refactor in mind, an issue first is
the friendlier path.

## Style

- Python: PEP 8 plus `flake8 --max-line-length=120`. `mypy` is run with
  `--ignore-missing-imports`. Type hints are encouraged on public API,
  not required on private helpers.
- Docstrings: Google style (`Args:`, `Returns:`, `Raises:` blocks).
- Markdown: prefer plain ASCII over typographic Unicode (avoid em-dashes,
  smart quotes, ellipsis). Wrap lines at ~80 columns when reasonable.
- Commit messages: `type(scope): subject`, e.g.
  `fix(syntax-filter): treat @SuppressWarnings as non-noise`.

## License

By submitting a contribution, you agree that it is released under the
project's MIT license.
