# Publishing

This repo is ready to publish when the PyPI credential exists. Until then, install
from GitHub:

```bash
pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"
```

## Preconditions

1. Create or access the `agent-contracts` project on PyPI.
2. Create a PyPI API token scoped to that project.
3. Add it to the GitHub repo as an Actions secret named `PYPI_API_TOKEN`.

No source changes are needed after the secret exists.

## Local verification

```bash
python3 -m pip install -e ".[dev]"
PYTHONPATH=. pytest -q
python3 -m build
python3 -m twine check dist/*
```

Expected package files:

- `dist/agent_contracts-<version>.tar.gz`
- `dist/agent_contracts-<version>-py3-none-any.whl`

## Publish path

Use one of these:

- Create a GitHub release; `.github/workflows/publish.yml` will build, check, and publish.
- Manually run the `publish` workflow from GitHub Actions.

The workflow fails closed if `PYPI_API_TOKEN` is missing.

## Version rule

Before publishing a new release:

1. Bump `version` in `pyproject.toml`.
2. Add a `CHANGELOG.md` entry.
3. Run the local verification commands.
4. Tag the release as `v<version>`.

Do not publish from a dirty worktree.
