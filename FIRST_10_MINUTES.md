# First 10 minutes

Use this path when you are evaluating whether `agent-contracts` is worth wiring
into an existing agent runtime. The goal is not to learn the whole library. The
goal is to see one bad action fail before it reaches a side effect.

## 1. Run the browser proof

Open the live playground:

```text
https://impartshadow.github.io/agent-contracts/playground/
```

Run these three scenarios:

| Scenario | Expected result | Why it matters |
|---|---|---|
| Write to `/etc/passwd` | `BLOCK` | Proves the gate can stop a dangerous tool call before execution |
| Leak an AWS key | `BLOCK` | Proves output text can be checked before it leaves the agent |
| Unverified "done" | `WARN` | Proves claims can be flagged when there is no evidence behind them |

If those results do not make sense for your runtime, stop here. This library is
for deterministic action boundaries, not broad judgment.

## 2. Run one local block

Install directly from GitHub until the PyPI package is published:

```bash
python -m pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"
```

Then run a pre-call check:

```bash
agent-contracts check-pre \
  --tool write_file \
  --params-json '{"path":"/etc/passwd","content":"x"}' \
  --json
```

Expected behavior:

- exit code: `1`
- `blocked`: `true`
- fired contract: `dangerous-path-guard`

Now run an allowed call:

```bash
agent-contracts check-pre \
  --tool write_file \
  --params-json '{"path":"notes.md","content":"x"}' \
  --json
```

Expected behavior:

- exit code: `0`
- `passed`: `true`
- no violations

## 3. Pick your first contract

Choose the first side effect that would hurt if the agent got it wrong:

| Your agent can... | Start with... | First proof |
|---|---|---|
| Write files | `WorkspacePathGuard` | Blocks writes outside the project root |
| Run shell commands | `ShellCommandGuard` | Blocks destructive shell patterns |
| Send email or Slack | custom recipient allowlist | Blocks unapproved recipients |
| Publish publicly | `SecretLeakGuard` + custom identity guard | Blocks leaked secrets and wrong persona |
| Mutate production data | custom environment/ticket guard | Blocks prod writes without explicit metadata |

Do not start with "make the agent better." Start with one boundary where a bad
call changes external state.

## 4. Wire the smallest real boundary

Put the check immediately before the side effect:

```python
from agent_contracts import ActionContext, Registry, WorkspacePathGuard

registry = Registry([WorkspacePathGuard("/srv/my-agent/workspace")])


def write_file(path: str, content: str):
    registry.enforce_pre(
        ActionContext(
            action="tool_call",
            tool="write_file",
            params={"path": path, "content": content},
        )
    )
    return real_write_file(path, content)
```

The contract belongs in the shared tool router or client, not in the prompt. If
the same side effect can happen through shell, browser automation, helper
scripts, and direct API calls, gate the shared lower-level path.

## 5. Add the adoption smoke test

The acceptance test is simple: the side effecting function must not run when the
contract blocks.

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

When this test passes in CI, you have a real boundary. Everything else is
expansion.

## 6. Then expand

After the first boundary works:

1. Gate every route into the same side effect.
2. Add `agent-contracts matrix` to CI.
3. Add `agent-contracts replay` against captured action logs.
4. Convert repeated warnings into narrow custom blocking contracts.

Useful next docs:

- [CI_INTEGRATION.md](CI_INTEGRATION.md)
- [ADOPTION_PLAYBOOK.md](ADOPTION_PLAYBOOK.md)
- [RECIPES.md](RECIPES.md)
- [THREAT_MODEL.md](THREAT_MODEL.md)
