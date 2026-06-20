# Contract Matrix

`agent-contracts` ships an executable matrix: one canonical scenario for each
built-in guard. This is the quickest way to prove the package is doing what the
README claims without reading the source.

```bash
agent-contracts matrix
agent-contracts matrix --json
```

Expected coverage:

| Scenario | Phase | Expected contract | Expected result |
|---|---|---|---|
| `repeated-file-edit` | pre | `loop-guard` | block |
| `system-path-write` | pre | `dangerous-path-guard` | block |
| `workspace-escape` | pre | `workspace-path-guard` | block |
| `root-shell-command` | pre | `shell-command-guard` | block |
| `raw-secret-in-params` | pre | `secret-leak-guard` | block |
| `unknown-tool-for-role` | pre | `tool-allowlist-guard` | block |
| `completion-claim-without-evidence` | post | `unverified-completion-guard` | warn |

The matrix is also importable:

```python
from agent_contracts import run_contract_matrix

rows = run_contract_matrix()
assert all(row["passed"] for row in rows)
```

Use it in CI when adopting the package. If a row fails, either a contract
regressed or your packaging/import path is not loading the version you think it
is.
