# CI Integration

Contracts should fail loudly when they drift. Put the matrix and one local
policy check in CI so the repository proves the boundary on every pull request.

## GitHub Actions

Fast path:

```bash
agent-contracts bootstrap --workspace "$(pwd)"
```

That writes `.github/workflows/agent-contracts.yml`, `agent-contracts.yml`, and
an importable adapter under `agent_contracts_scaffold/`.

Manual path:

Copy [`examples/github_actions_contracts.yml`](examples/github_actions_contracts.yml)
to `.github/workflows/agent-contracts.yml` in the repo that owns your agent.

The workflow does three things:

1. Installs `agent-contracts` from the public GitHub repo.
2. Runs `agent-contracts matrix` to prove every built-in contract fires.
3. Generates a workspace policy and verifies one allowed path plus one blocked
   workspace escape.

If your agent already emits JSONL action records, add `agent-contracts replay`
as the next CI step. Use `--expect-blocks` for incident fixtures so CI passes
only when the same bad call still blocks after every policy edit.

## Minimal inline version

```yaml
name: agent-contracts

on: [pull_request]

jobs:
  contract-matrix:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"
      - run: agent-contracts matrix
      - run: agent-contracts replay examples/actions.jsonl --expect-blocks 1
        if: hashFiles('examples/actions.jsonl') != ''
```

## What to add after the smoke test

Once the matrix is passing, add one test at the exact tool boundary in your
runtime:

```python
import pytest

from agent_contracts import BlockedAction, ContractedToolRouter


def test_guard_blocks_before_side_effect():
    called = False

    def write_file(path, content):
        nonlocal called
        called = True

    router = ContractedToolRouter({"write_file": write_file})

    with pytest.raises(BlockedAction):
        router.call("write_file", {"path": "/etc/passwd", "content": "x"})

    assert called is False
```

That last assertion is the adoption bar: the contract must block before the side
effecting function runs.
