# Quickstart — 60 seconds to your first blocked action

## 1. Install

```bash
pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"
# or, from a clone:
pip install -e .
```

No dependencies. It's pure Python, 3.9+.

Smoke test the install:

```bash
python3 -m agent_contracts
# after install, these console scripts work too:
agent-contracts
agent-contracts-demo
```

## 2. Block a dangerous tool call

```python
from agent_contracts import Registry, ActionContext, default_contracts

registry = Registry(default_contracts())

ctx = ActionContext(
    action="tool_call",
    tool="write_file",
    params={"path": "/etc/cron.d/backdoor", "content": "* * * * * root ..."},
)

result = registry.check_pre(ctx)
print(result.blocked)            # True
print(result.violations[0])      # dangerous-path-guard → write to protected path '/etc/...'
```

That's the whole idea. You hand the registry the action your agent is *about* to
take, and it tells you whether to let it through — before anything touches the disk.

## 3. Run the same check from shell or CI

```bash
agent-contracts check-pre \
  --tool write_file \
  --params-json '{"path": "/etc/cron.d/backdoor", "content": "* * * * * root ..."}' \
  --json
```

The command exits `1` when a blocking contract fires and `0` when the action is
clean or only warning-level checks fire.

Run the built-in contract matrix:

```bash
agent-contracts matrix
```

For pull-request coverage, copy
[`examples/github_actions_contracts.yml`](examples/github_actions_contracts.yml)
into `.github/workflows/agent-contracts.yml`. The full CI path is in
[CI_INTEGRATION.md](CI_INTEGRATION.md).

## 4. Generate a starter policy

```bash
agent-contracts init --workspace "$(pwd)"
```

This writes `agent-contracts.yml` with the default workspace boundary, tool
allowlist, shell-tool names, loop limit, completion-evidence rule, and secret
leak settings. Treat it as an adoption checklist: delete what does not apply,
then wire the surviving entries into your agent's shared tool router.

Run checks against that policy:

```bash
agent-contracts check-pre \
  --policy agent-contracts.yml \
  --tool send_email \
  --params-json '{}'
```

Or load it in Python:

```python
from agent_contracts import load_policy

registry = load_policy("agent-contracts.yml")
```

## 5. Wire it into your agent loop

Two lines around every tool call:

```python
from agent_contracts import BlockedAction

def run_tool(tool, params):
    ctx = ActionContext(action="tool_call", tool=tool, params=params)
    registry.enforce_pre(ctx)        # raises BlockedAction if a contract blocks
    return actually_run(tool, params)
```

And one check on every reply the agent produces:

```python
def emit(reply_text):
    result = registry.check_post(ActionContext(action="respond", response_text=reply_text))
    if result.blocked:
        reply_text = regenerate_or_redact(reply_text, result.violations)
    return reply_text
```

`check_pre` stops bad *actions*; `check_post` catches bad *output* (a leaked key, a
false "done" claim). That's the entire surface area.

## 6. Add your own line in the sand

```python
from agent_contracts import Contract, Severity

class NoProdDeletes(Contract):
    name = "no-prod-deletes"
    def check_pre(self, ctx):
        if ctx.tool == "run_sql" and "drop table" in ctx.params.get("query", "").lower():
            return self._violation(
                "DROP TABLE from the agent is not allowed",
                severity=Severity.BLOCK,
                recovery="Open a migration PR for a human.",
            )

registry.register(NoProdDeletes())
```

Now `DROP TABLE` from the agent is a regex and an `if` — not a second model you hope
is paying attention.

## Next

- See every default guard and the design rationale in the [README](README.md).
- Wiring this into a real tool dispatcher? Use [INTEGRATION_PATTERNS.md](INTEGRATION_PATTERNS.md).
- Adding this to CI? Use [CI_INTEGRATION.md](CI_INTEGRATION.md).
- Using OpenAI tool calls, LangChain, AutoGen, CrewAI, or a raw CLI agent? Use [FRAMEWORK_ADAPTERS.md](FRAMEWORK_ADAPTERS.md).
- Auditing an existing agent? Start with [AUDIT_CHECKLIST.md](AUDIT_CHECKLIST.md).
- See the production failure log that motivated each guard in [FAILURE_MODES.md](FAILURE_MODES.md).
- Deciding between this and Guardrails AI / NeMo / LlamaFirewall? [COMPARISON.md](COMPARISON.md).
- Run the live demos: `python3 -m agent_contracts`, `agent-contracts check-pre`,
  `python examples/demo.py`, `python examples/policy_loader.py`, and
  `python examples/openai_tool_call_adapter.py`.
