# Agent contracts adoption playbook

Use this when you need to decide whether deterministic contracts belong in an
existing agent runtime. The goal is not to redesign the agent. The goal is to put
one hard gate in front of one real side effect, prove it blocks the failure, and
decide whether to expand.

## The one-afternoon evaluation

Time box: 90 minutes.

Outcome: a working pre-call gate around one side-effecting tool.

### 0-30 minutes: pick the first boundary

Choose one tool where a bad call would create real damage.

Good first targets:

| Tool class | Why it is first | First contract |
|---|---|---|
| File writes | Easy to test, easy to bypass if only prompt-gated | `WorkspacePathGuard` |
| Shell commands | High blast radius, common escape hatch | `ShellCommandGuard` |
| External email or Slack | Wrong-recipient mistakes are irreversible | custom recipient allowlist |
| Public publishing | Leaks and wrong persona become external artifacts | custom identity/dox guard |
| Production SQL | One bad mutation beats a thousand safe reads | custom environment/ticket guard |

Do not start with vague "agent quality." Start with a concrete action that
changes external state.

### 30-60 minutes: wire the shared dispatcher

Find the lowest common point before the side effect executes.

Good placement:

```text
agent plan -> tool router -> contract check -> actual tool/API/client
```

Weak placement:

```text
agent prompt -> model self-review -> tool router -> actual tool/API/client
```

If the same side effect can happen through shell, browser automation, helper
scripts, and direct API calls, gate the shared client or dispatcher. A contract on
only one pretty path is a demo, not a boundary.

Minimal wiring:

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

### 60-90 minutes: prove the gate

Add two tests before trusting the contract:

1. A blocked case that recreates the failure you care about.
2. An allowed case that proves normal work still runs.

Example:

```python
from agent_contracts import ActionContext, BlockedAction, Registry, WorkspacePathGuard


def test_blocks_write_outside_workspace():
    registry = Registry([WorkspacePathGuard("/tmp/workspace")])
    ctx = ActionContext(
        action="tool_call",
        tool="write_file",
        params={"path": "/etc/passwd", "content": "no"},
    )
    try:
        registry.enforce_pre(ctx)
    except BlockedAction:
        return
    raise AssertionError("expected BlockedAction")


def test_allows_write_inside_workspace():
    registry = Registry([WorkspacePathGuard("/tmp/workspace")])
    ctx = ActionContext(
        action="tool_call",
        tool="write_file",
        params={"path": "/tmp/workspace/notes.md", "content": "ok"},
    )
    registry.enforce_pre(ctx)
```

## Acceptance criteria

Ship the first contract only when all five are true:

| Criterion | Bar |
|---|---|
| Boundary | The contract runs before the actual side effect, not after the agent explains itself |
| Coverage | The common dispatcher/client path is gated, not only one call site |
| Determinism | The decision depends on explicit state, regex, paths, allowlists, counters, or metadata |
| Recovery | A block maps to a specific safe next action |
| Tests | At least one blocked case and one allowed case are in CI |

## Kill criteria

Do not use this library as the primary solution when the thing you need is:

| Need | Use instead |
|---|---|
| Sandboxed code execution | containers, seccomp, Firecracker, gVisor, E2B-style sandboxes |
| Human-quality content review | a human review workflow or a model judge behind deterministic hard gates |
| Prompt-injection classification | model-based classifiers plus least-privilege tools |
| Full data-loss prevention | DLP tooling at storage, network, and identity layers |
| Fine-grained cloud authorization | IAM, service accounts, scoped tokens, policy-as-code |

Contracts are for the lines that must not move. They are not a replacement for a
sandbox, IAM, or human judgment.

## Expansion path

After the first gate works, expand in this order:

1. Gate every route into the same side effect.
2. Add post-condition checks for claims and outbound text.
3. Add structured violation logging.
4. Count which contracts fire most often.
5. Promote repeated WARN violations into BLOCK only after you understand the false
   positives.

The practical standard is simple: after adoption, a bad action should fail before
it touches the outside world, and the failure should be boring enough to test.
