# CleanTest-Agent v0.1.1

First PyPI-published release.

## Install

```bash
pip install cleantest-agent
```

That command worked starting with this release. v0.1.0 was a
source-only release on GitHub.

## What changed since v0.1.0

This is a packaging release. No public API or numerical claim has
changed; the pipeline, skills, and Filter 3 model-mode metrics are
identical to v0.1.0. The reason for cutting it as a new version is
that PyPI does not accept the v0.1.0 sdist + wheel built before the
metadata migration described below, and PyPI does not allow
re-uploading under an existing version number.

### Packaging

- **Migrated to PEP 639** for license metadata.
  `pyproject.toml` now declares `license = "MIT"` and
  `license-files = ["LICENSE"]`; the legacy
  `License :: OSI Approved :: MIT License` classifier is removed.
- **Bumped build-backend pin** to `setuptools >= 77`, the first
  release with full PEP 639 support.
- **Expanded classifiers** with `Development Status :: 4 - Beta`,
  `Intended Audience :: Developers`, `Intended Audience :: Science/Research`,
  and `Topic :: Scientific/Engineering :: Artificial Intelligence`.
- **Broadened keywords** with `test-generation`, `skill-md`,
  `methods2test`, `tree-sitter`, and `aho-corasick`.
- **Added Project URLs**: `Documentation`, `Issues`, `Changelog`,
  and a direct link to the v0.1.0 paper PDF asset.
- **Tightened the description** to a single concrete sentence:
  "Rule-first three-filter pipeline for cleaning unit-test training
  data, packaged as four SKILL.md skills."

### CD pipeline

- **New tag-driven publish workflow** at
  `.github/workflows/publish.yml`. Pushing a `v*` tag triggers
  build -> `twine check --strict` -> upload to PyPI via OIDC
  Trusted Publisher (no API token) -> sigstore keyless signing ->
  attach signed sdist + wheel + sigstore bundles to the matching
  GitHub Release with `gh release upload --clobber`.
- **Operations runbook** added at `docs/PYPI-PUBLISHING.md`:
  one-time Trusted Publisher claim, per-release tagging flow, local
  dry-run checklist, offline sigstore verification command, and the
  yank-vs-delete policy.

### Documentation

- **PyPI-friendly README**. The hero image now references
  `raw.githubusercontent.com` instead of a repo-relative path so it
  renders on the PyPI project page. The Quick Start section leads
  with `pip install cleantest-agent` and demotes the source-install
  path to a "for development" alternative.
- **PyPI version badge** added between the CI badge and the Python
  versions badge.

## CI / quality

- All flake8 (`F401`) and mypy (`union-attr`, `return-value`)
  warnings flagged on the v0.1.0 push are fixed.
- GitHub Actions matrix runs green on Python 3.10, 3.11, and 3.12.
- `actions/checkout`, `actions/setup-python`, and
  `codecov/codecov-action` bumped to Node.js 24-compatible versions
  (v5 / v6 / v5).

## Verifying the published wheel

To confirm a clean install works:

```bash
python -m venv /tmp/cta-verify && source /tmp/cta-verify/bin/activate
pip install cleantest-agent==0.1.1
cleantest --help
python -c "import cleantest_agent; print('ok')"
```

To verify the sigstore signature offline:

```bash
pip install sigstore
sigstore verify identity \
    --bundle cleantest_agent-0.1.1-py3-none-any.whl.sigstore.json \
    --cert-identity 'https://github.com/jimmy0717/cleantest-agent/.github/workflows/publish.yml@refs/tags/v0.1.1' \
    --cert-oidc-issuer 'https://token.actions.githubusercontent.com' \
    cleantest_agent-0.1.1-py3-none-any.whl
```

## Citation

The bibtex stanza for this release is unchanged from v0.1.0; this
is a packaging release, not a new artefact.

## Acknowledgements

Same as v0.1.0. See
<https://github.com/jimmy0717/cleantest-agent/releases/tag/v0.1.0>.

---

**Git tag**: `v0.1.1`
**Date**: 2026-05-24
