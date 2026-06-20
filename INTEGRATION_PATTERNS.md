# Integration patterns

`agent-contracts` belongs at the boundary where an agent is about to touch the
outside world. Do not bury it in prompt text. Do not ask a second model to decide
whether a tool call is safe. Convert the intended action into an `ActionContext`,
run a deterministic gate, then dispatch only if the gate passes.

## 1. Tool router boundary

This is the highest-leverage integration point for most systems:

```python
from agent_contracts import ActionContext, BlockedAction, Registry, default_contracts

registry = Registry(default_contracts())

def run_tool(tool_name, params):
    ctx = ActionContext(action="tool_call", tool=tool_name, params=params)
    registry.enforce_pre(ctx)   # raises BlockedAction if a BLOCK contract fires
    return dispatch(tool_name, params)
```

Use this around file writes, shell commands, database calls, browser automation,
email sends, publishing actions, and payment operations. Anything with side
effects should pass through the same gate.

Runnable example: [`examples/tool_router.py`](examples/tool_router.py).

If an agent role should only be able to call a narrow tool set, register
`ToolAllowlistGuard` at the same boundary:

```python
from agent_contracts import ToolAllowlistGuard

registry.register(ToolAllowlistGuard({"read_file", "web_search", "summarize"}))
```

## 2. Response boundary

Pre gates stop bad actions. Post gates catch bad output before it leaves your
system:

```python
def emit_user_response(text):
    result = registry.check_post(ActionContext(action="respond", response_text=text))
    if result.blocked:
        return regenerate_or_redact(text, result.violations)
    return text
```

The default post gate catches likely secret leaks and warns on unverified
completion claims. In production, store WARN violations too. They are often the
early signal that the agent is learning to say "done" faster than it proves done.

## 3. State-aware gates

The most useful contracts are usually specific to your runtime. `ActionContext`
has fields for the state that generic guardrails need:

- `files_written`: paths touched this turn
- `tool_calls`: tools already called this turn
- `edits_by_path`: per-path edit counts
- `metadata`: app-specific state, such as environment, account, channel, or risk tier

Example: block production database writes unless the caller supplied an explicit
change-ticket id.

```python
from agent_contracts import Contract

class ProdDatabaseWriteGuard(Contract):
    name = "prod-database-write-guard"

    def check_pre(self, ctx):
        if ctx.tool != "run_sql":
            return None
        if ctx.metadata.get("environment") != "prod":
            return None
        if ctx.metadata.get("change_ticket"):
            return None
        return self._violation(
            "production SQL requires a change_ticket in ActionContext.metadata",
            recovery="Attach the approved ticket or run against a non-prod database.",
        )
```

## 4. Human escalation boundary

Contracts should be precise about what happens after a block. A blocked action is
not a vague refusal; it is a routed outcome:

```python
try:
    return run_tool(tool_name, params)
except BlockedAction as exc:
    return {
        "status": "blocked",
        "violations": [v.contract for v in exc.violations],
        "recovery": [v.recovery for v in exc.violations if v.recovery],
    }
```

Good recovery text tells the agent what to do next: write inside the workspace,
redact the token, open a PR, ask for explicit approval, or switch to a reversible
path.

## 5. Where not to put it

Do not rely on contracts in these places:

- **Only in the prompt.** The model can ignore, forget, or reinterpret prompt rules.
- **Only after execution.** Post-hoc detectors are useful for leaks, but too late for
  destructive actions.
- **Only in one tool path.** If file writes can happen through `write_file`,
  `apply_patch`, shell redirection, and a browser upload, gate every path or move
  the contract to the shared dispatcher.
- **As a complete sandbox.** Contracts are a governance layer, not a kernel,
  container, permission system, or secrets manager.

## 6. Minimum production checklist

- Gate every side-effecting tool call with `registry.enforce_pre(...)`.
- Gate every final user-visible response with `registry.check_post(...)`.
- Log every violation, including WARN severity.
- Give every custom contract a short recovery instruction.
- Add tests for both block and pass cases.
- Keep contracts deterministic: no LLM calls, no sampling, no hidden network
  dependency in the check itself.
