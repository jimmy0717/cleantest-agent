# Publishing CleanTest-Agent to PyPI

This project ships a tag-driven CD pipeline at
`.github/workflows/publish.yml`. Pushing a `v*` tag (e.g. `v0.1.1`)
will:

1. build sdist + wheel with `pypa/build`,
2. validate metadata with `twine check --strict`,
3. upload to PyPI via OIDC Trusted Publisher (no API token),
4. sign the artefacts with `sigstore` (keyless, OIDC),
5. upload the signed sdist + wheel + sigstore bundles to the matching
   GitHub Release with `gh release upload --clobber`.

The pipeline is gated on a one-time PyPI Trusted Publisher claim that
must be configured before the first tag push. The recipe is below.

## One-time setup (5 minutes, owner-only)

### 1. Reserve the PyPI project name

The package name `cleantest-agent` was unclaimed at the time of
v0.1.0 (HTTP 404 on `pypi.org/pypi/cleantest-agent/json`). Reserve it
by completing step 2 below. No prior `twine upload` is needed.

### 2. Register the GitHub Trusted Publisher

1. Sign in at <https://pypi.org> with the account that should own the
   project (the same email used in `pyproject.toml`'s `authors`).
2. Go to **Account settings -> Publishing -> Add a new pending
   publisher** (URL: <https://pypi.org/manage/account/publishing/>).
3. Fill the form with **exactly** these values:

   | Field          | Value                |
   |----------------|----------------------|
   | PyPI Project   | `cleantest-agent`    |
   | Owner          | `jimmy0717`          |
   | Repository     | `cleantest-agent`    |
   | Workflow name  | `publish.yml`        |
   | Environment    | `pypi`               |

4. Click **Add**. The publisher is now in *pending* state. The first
   successful run of `publish.yml` automatically promotes it to
   *active* and creates the project on PyPI.

### 3. (Optional) Configure the GitHub deployment environment

The workflow declares `environment: pypi`. If you want a one-click
manual approval gate before each publish, create the environment in
the repo settings:

1. <https://github.com/jimmy0717/cleantest-agent/settings/environments>
2. **New environment** -> name `pypi`.
3. (Optional) tick **Required reviewers** and add yourself; PyPI
   uploads will then pause until you approve them in the Actions UI.

If you skip this step the workflow still works; it just publishes
without the manual gate.

## Cutting a release

The repository version source of truth is `pyproject.toml`'s
`[project] version`. To cut a release:

```bash
# 1. Bump the version in pyproject.toml
$EDITOR pyproject.toml          # e.g. 0.1.0 -> 0.1.1

# 2. Update docs/RELEASE-NOTES-v<X.Y.Z>.md (or add a new file)

# 3. Commit and tag
git add pyproject.toml docs/RELEASE-NOTES-v0.1.1.md
git commit -m "release: v0.1.1"
git tag -a v0.1.1 -m "v0.1.1: <one-line summary>"

# 4. Push branch and tag in one go
git push && git push origin v0.1.1

# 5. Create the GitHub Release shell (the tag-driven publish.yml
#    will then attach signed sdist + wheel + sigstore bundles to it)
gh release create v0.1.1 \
    --title "v0.1.1 - <short title>" \
    --notes-file docs/RELEASE-NOTES-v0.1.1.md
```

After the tag push, watch <https://github.com/jimmy0717/cleantest-agent/actions/workflows/publish.yml>.
A green run will land the artefacts on
<https://pypi.org/project/cleantest-agent/> within 1 - 2 minutes and
attach `cleantest_agent-X.Y.Z.tar.gz`, `cleantest_agent-X.Y.Z-py3-none-any.whl`,
and the matching `.sigstore.json` bundles to the GitHub Release.

## Local dry run (before tagging)

To verify the build works locally without touching PyPI:

```bash
pip install build twine
rm -rf dist build *.egg-info
python -m build
python -m twine check --strict dist/*
```

`twine check --strict` will reject any README rendering issues that
PyPI would also reject. The artefacts under `dist/` are byte-identical
to what the workflow produces.

## Verifying a published package

To confirm a release on a clean machine:

```bash
python -m venv /tmp/cta-verify && source /tmp/cta-verify/bin/activate
pip install cleantest-agent==0.1.1
cleantest --help
python -c "import cleantest_agent; print(cleantest_agent.__version__)"
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

## Yanking a broken release

If a published version contains a regression that should be hidden
from `pip install cleantest-agent` (without breaking pinned installs),
**yank** rather than delete:

1. <https://pypi.org/manage/project/cleantest-agent/release/X.Y.Z/>
2. Click **Yank**.
3. Bump to `X.Y.(Z+1)` and re-publish via the normal tag flow.

PyPI does not allow re-uploading a yanked or deleted version under
the same number.

## Why OIDC Trusted Publisher and not an API token

- **No long-lived secrets** in the repo or in GitHub Actions secrets.
- **Scoped to one workflow file** (`publish.yml`); a compromised PR
  cannot publish even by adding a `pypa/gh-action-pypi-publish` step
  in another workflow.
- **No rotation**; the OIDC ID-token is exchanged per-run and expires
  in minutes.
- **Public attestations** (PEP 740): the artefacts shipped to PyPI
  carry a verifiable claim that they came from this exact repo, this
  exact tag, this exact workflow file, signed by GitHub's OIDC issuer.
