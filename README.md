# agent-contracts

[![tests](https://github.com/impartshadow/agent-contracts/actions/workflows/tests.yml/badge.svg)](https://github.com/impartshadow/agent-contracts/actions/workflows/tests.yml)
![Agent reliability: 95/100](https://img.shields.io/badge/agent%20reliability-95%2F100-brightgreen)

**Deterministic pre/post-condition guardrails for LLM agents. No model in the loop.**

> **▶ [Try it in your browser — no install](https://impartshadow.github.io/agent-contracts/playground/)** · paste an agent action, watch a real contract block it (runs the actual engine via Pyodide).
>
> **Evaluating quickly?** Start with [FIRST_10_MINUTES.md](FIRST_10_MINUTES.md):
> browser proof, one local block, one CI-ready adoption test.
>
> **Want the public scorecard path?** Run `agent-contracts score --root .`.
> It emits a 0-100 reliability score plus a markdown badge you can put in a README.
> Add `--output-json agent-reliability-score.json --output-markdown AGENT_RELIABILITY_SCORE.md --output-badge-json agent-reliability-badge.json`
> to publish a reusable scorecard artifact.

Most agent "safety" layers ask a model to police a model — a second LLM call that
reviews the first one's output. That fails in exactly the moment you need it: when
the model is confused, jailbroken, or looping, the reviewer is running on the same
bad context. `agent-contracts` takes the other path. A **contract** is a plain
Python function over the action context. It runs the same way every time, costs
nothing, and can't be talked out of its decision.

![agent-contracts blocking a dangerous write and a leaked key in real time](docs/demo.svg)

```python
from agent_contracts import Registry, ActionContext, default_contracts

registry = Registry(default_contracts())

# before a tool call runs:
ctx = ActionContext(action="tool_call", tool="write_file",
                    params={"path": "/etc/passwd", "content": "..."})

result = registry.check_pre(ctx)
if result.blocked:
    for v in result.violations:
        print(v.contract, "→", v.message)
# dangerous-path-guard → write to protected path '/etc/passwd' (matched '/etc/')
```

## The model

Two gates around every agent action:

- **`check_pre`** runs *before* a tool executes. Use it to stop dangerous calls —
  writes to system paths, runaway edit loops, secrets in arguments.
- **`check_post`** runs *after* the agent produces output. Use it to catch what
  leaked — credentials in a reply, a "done" claim with nothing to back it.

A contract returns a `Violation` (with `severity` `BLOCK` or `WARN`) or `None`.
The `Registry` runs them all and collects every violation — no short-circuit, so
you see the full picture of what a single action tripped.

```python
result = registry.check_pre(ctx)
result.passed     # True if nothing fired
result.blocked    # True if any BLOCK-severity violation fired
result.violations # list[Violation]
result.to_dict()  # JSON-serializable payload for logs/API responses
```

To make blocking automatic, wrap the call with `enforce_pre`, which raises
`BlockedAction` if anything blocks:

```python
from agent_contracts import BlockedAction

try:
    registry.enforce_pre(ctx)
    run_the_tool(ctx.tool, ctx.params)
except BlockedAction as e:
    handle_refusal(e.violations)
```

If you want a copy-paste router instead of wiring the boundary yourself:

```python
from agent_contracts import ContractedToolRouter

router = ContractedToolRouter({"write_file": write_file})
router.call("write_file", {"path": "notes.md", "content": "ship it\n"})

# Raises BlockedAction before write_file ever runs:
router.call("write_file", {"path": "/etc/passwd", "content": "nope"})
```

## What ships in the box

| Contract | Phase | Catches |
|---|---|---|
| `LoopGuard` | pre | An agent rewriting the same file over and over |
| `DangerousPathGuard` | pre | Writes to `/etc`, `/usr`, `~/.ssh`, `~/.aws`, … |
| `WorkspacePathGuard` | pre | File actions that escape a configured workspace root |
| `ShellCommandGuard` | pre | Obvious high-blast-radius shell commands (`sudo`, `rm -rf /`, `mkfs`, protected redirects) |
| `SecretLeakGuard` | pre + post | Private keys, AWS/GitHub/Slack/Stripe tokens, `KEY=…` env lines |
| `UnverifiedCompletionGuard` | post | "Done / shipped / fixed" with no output, URL, hash, or path (warn) |
| `ToolAllowlistGuard` | pre | Tool calls outside an explicit role/tool allowlist |

These are starting points, not a finished security boundary. Read them, copy them,
tighten them for your own system.

> **Where these contracts come from:** every guard here exists because an agent
> failed in a specific, repeated way in production. The full taxonomy — 13 named
> failure modes, worst-first, including the ones that *can't* be solved with code —
> is in **[FAILURE_MODES.md](FAILURE_MODES.md)**. It's the most useful page in the repo.
>
> **Evaluating against Guardrails AI / NeMo Guardrails / LlamaFirewall?**
> [COMPARISON.md](COMPARISON.md) is an honest map of where this fits and when to use
> something else — read the "use X instead when" lines first.
>
> **Wiring this into an existing agent loop?** Start with
> [INTEGRATION_PATTERNS.md](INTEGRATION_PATTERNS.md). It shows where the gate belongs:
> the shared tool router, not another prompt instruction.
>
> **Using OpenAI tool calls, LangChain, AutoGen, CrewAI, or a raw CLI agent?**
> [FRAMEWORK_ADAPTERS.md](FRAMEWORK_ADAPTERS.md) gives copy-paste adapter shapes.
>
> **Putting contracts in front of MCP tools or an agent gateway?**
> [MCP_ADAPTER.md](MCP_ADAPTER.md) shows the shared-dispatcher boundary.
>
> **Auditing your own agent first?** Use [AUDIT_CHECKLIST.md](AUDIT_CHECKLIST.md)
> to find the side-effecting tools that need contracts before anything else.
>
> **Only have ten minutes?** [FIRST_10_MINUTES.md](FIRST_10_MINUTES.md) gives the
> shortest path from "what is this?" to one blocked side effect in your runtime.
>
> **Evaluating whether to adopt this in an existing runtime?**
> [ADOPTION_PLAYBOOK.md](ADOPTION_PLAYBOOK.md) gives a 90-minute path, acceptance
> criteria, and kill criteria.
>
> **Need to verify a generated policy/scaffold/CI setup?**
> Run `agent-contracts doctor --root .` for a read-only adoption report.
> `agent-contracts bootstrap` also writes optional local pre-commit hooks for
> `matrix` and `doctor` when your repo already uses pre-commit.
>
> **Want a badge and public score?**
> Run `agent-contracts score --root . --badge`. The score weights required
> adoption wiring, the built-in contract matrix, optional labeled evals, and
> optional incident replay. The seed public table is [LEADERBOARD.md](LEADERBOARD.md).
> CI can upload the full scorecard using the workflow in
> [.github/workflows/agent-contracts.yml](.github/workflows/agent-contracts.yml).
>
> **Need copy-paste custom contracts?** [RECIPES.md](RECIPES.md) has recipient,
> production SQL, evidence-before-blocker, and public publishing identity guards.
>
> **Want executable proof that every built-in guard fires?**
> [CONTRACT_MATRIX.md](CONTRACT_MATRIX.md) documents `agent-contracts matrix`,
> the CI-friendly scenario matrix.
>
> **Want measurable precision/recall on your own incident corpus?**
> [EVALUATION.md](EVALUATION.md) documents `agent-contracts eval`, a labeled
> JSONL harness for false positives, false negatives, and expected-contract misses.
>
> **Want to audit existing agent logs before live wiring?**
> [REPLAY.md](REPLAY.md) documents `agent-contracts replay`, a JSONL replay path
> for checking historical tool calls and responses against a policy.
>
> **Want pull requests to prove the boundary still works?**
> [CI_INTEGRATION.md](CI_INTEGRATION.md) gives a copy-paste GitHub Actions workflow.
>
> **Want to measure the overhead locally?**
> [PERFORMANCE.md](PERFORMANCE.md) documents `examples/benchmark.py`.
>
> **Need to know what this does *not* protect?** Read
> [THREAT_MODEL.md](THREAT_MODEL.md) before treating contracts as a security
> boundary. They are action gates, not a sandbox.
>
> **Want to add a contract?** [CONTRIBUTING.md](CONTRIBUTING.md) lays out the bar:
> deterministic, narrow, tested, and tied to a real agent failure mode.
>
> **Reporting a bypass or bad security claim?** Use [SECURITY.md](SECURITY.md)
> for the supported scope and reporting standard.
>
> **Tracking what changed?** Read [CHANGELOG.md](CHANGELOG.md).
> Latest release notes: [v0.1.1](docs/releases/v0.1.1.md).
>
> **Publishing the package?** [PUBLISHING.md](PUBLISHING.md) documents the PyPI
> token, release workflow, and verification path.
>
> **Sharing the project?** [DISTRIBUTION_PACK.md](DISTRIBUTION_PACK.md) has
> copy-ready posts, reply snippets, and the canonical links.

## Writing your own

Subclass `Contract` and override whichever phase you need:

```python
from agent_contracts import Contract, ActionContext, Severity

class NoProductionDeletes(Contract):
    name = "no-prod-deletes"

    def check_pre(self, ctx: ActionContext):
        if ctx.tool == "run_sql" and "drop table" in ctx.params.get("query", "").lower():
            return self._violation(
                "DROP TABLE against production is not allowed from the agent",
                severity=Severity.BLOCK,
                recovery="Open a migration PR for a human to review.",
            )
        return None

registry.register(NoProductionDeletes())
```

Or lock an agent role to a narrow tool set:

```python
from agent_contracts import ToolAllowlistGuard

registry.register(ToolAllowlistGuard({"read_file", "web_search", "summarize"}))
```

Or force file actions to stay inside one project directory:

```python
from agent_contracts import WorkspacePathGuard

registry.register(WorkspacePathGuard("/srv/my-agent/workspace"))
```

`ActionContext` carries the action name, tool, params, response text, the user
message, files written, tools called this turn, and a per-path edit counter. A
`metadata` dict is there as an escape hatch for whatever your app needs to gate on.

## Why deterministic

A guardrail you can argue with isn't a guardrail. The whole value of a contract is
that the answer doesn't depend on a sampling temperature. When an agent is mid-loop
at 2am, you want the gate that blocks `DROP TABLE` to be a regex and an `if`, not a
second model that might be feeling agreeable. Use models for judgment; use contracts
for the lines that must not move.

## Install

```bash
pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"
# or, from a local clone:
pip install -e .
```

New here? **[QUICKSTART.md](QUICKSTART.md)** gets you from install to a blocked
action in under a minute.

To scaffold a real repository boundary in one command:

```bash
agent-contracts bootstrap --workspace "$(pwd)"
```

That writes:

- `agent-contracts.yml` — editable local policy
- `.github/workflows/agent-contracts.yml` — CI proof that the matrix and one workspace escape check fire
- `agent_contracts_scaffold/adapter.py` — importable `gate_tool_call` / `gate_response` helpers
- `agent_contracts_scaffold/README.md` — the exact wiring point and adoption bar

Run the tests and the demo:

```bash
pip install -e ".[dev]"
pytest -q
python3 -m agent_contracts
agent-contracts-demo
agent-contracts check-pre --tool write_file --params-json '{"path": "/etc/passwd"}'
agent-contracts init --workspace "$(pwd)"
agent-contracts bootstrap --workspace "$(pwd)"
agent-contracts doctor --root .
agent-contracts check-pre --policy agent-contracts.yml --tool send_email --params-json '{}'
agent-contracts matrix
agent-contracts eval examples/eval_corpus.jsonl
agent-contracts replay examples/actions.jsonl --expect-blocks 1
python3 examples/demo.py
python3 examples/tool_router.py
python3 examples/workspace_guard.py
python3 examples/policy_loader.py
python3 examples/openai_tool_call_adapter.py
python3 examples/mcp_tool_adapter.py
python3 examples/benchmark.py --iterations 10000
```

## Where this came from

This is the contract layer, extracted and generalized, from **Shadow** — an
autonomous agent running a real business in public (trading, content, research)
under a 100+ contract governance layer. The guardrails here are the load-bearing
ones, cleaned up for general use. If you want to watch the system that runs on
them: [echofromshadow.substack.com](https://echofromshadow.substack.com).

## License

MIT.
