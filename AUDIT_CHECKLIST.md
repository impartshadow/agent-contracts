# Agent safety audit checklist

Use this before adding another model-based evaluator. Most agent failures are not
subtle; they are side effects that should have been stopped at the boundary.

The goal is to leave with a short list of contracts to write first.

## 1. Find every side-effecting tool

List every tool your agent can call that changes outside state.

| Tool | Side effect | Current gate | Contract needed |
|---|---|---|---|
| `write_file` | Writes local files | ? | path guard, loop guard |
| `run_shell` | Executes commands | ? | command allowlist, protected path guard |
| `send_email` | Sends external email | ? | recipient guard, dox guard |
| `publish_post` | Publishes public text | ? | identity leak guard, quality gate |
| `run_sql` | Changes database state | ? | environment + change-ticket guard |
| `browser_click` | Acts in web sessions | ? | domain/action allowlist |

If the same effect can happen through multiple tools, gate the shared dispatcher.
Do not gate only the prettiest path.

## 2. Ask the five boundary questions

For each side-effecting tool, answer these with evidence from code:

1. **Where is the last point before the action executes?**  
   That is where `registry.enforce_pre(...)` belongs.

2. **Can the agent reach the same action through shell, browser, API, and helper
   scripts?**  
   If yes, the contract belongs below those routes, not inside one route.

3. **What context does the gate need?**  
   Put it in `ActionContext`: `tool`, `params`, `files_written`, `tool_calls`,
   `edits_by_path`, and `metadata`.

4. **What happens when it blocks?**  
   A block should produce a routed outcome: retry safely, redact, switch to a
   reversible path, open a PR, or escalate to a human.

5. **Is the check deterministic?**  
   If the rule is a hard line, keep it out of the model. Regex, path checks,
   allowlists, counters, and explicit metadata beat "ask another LLM."

## 3. Score your current system

Give each row a score from 0 to 2.

| Surface | 0 | 1 | 2 |
|---|---|---|---|
| File writes | No central gate | Some write paths gated | Every write path gated below the router |
| Shell commands | Free-form shell | Prompt rule / command review | Pre-call allowlist and path/secret scan |
| Secrets | Secrets can enter prompts/replies | Post-hoc scanner only | Pre + post scanner at outbound/tool boundary |
| Completion claims | Trusts agent prose | Requires some evidence | Blocks/warns claims without URL/hash/output/path |
| External sends | Agent chooses recipients/content | Manual review | Recipient + identity leak + quality gates |
| Repeated edits | No loop detection | Human notices loops | Per-path edit counter trips automatically |
| Database writes | Agent can run prod SQL | Environment warning | Environment + ticket + mutation contract |
| Human escalation | Vague refusals | Ad hoc escalation | BlockedAction maps to explicit recovery paths |

Score:

- **0-5:** You do not have guardrails. You have instructions.
- **6-10:** You have partial gates, probably bypassable by alternate tool paths.
- **11-14:** You have a usable deterministic floor.
- **15-16:** You are ready to layer model-based detectors behind the hard gates.

## 4. Map failures to first contracts

Start with the failures that are cheap to catch and expensive to miss.

| Failure | First contract |
|---|---|
| Writes to protected paths | `DangerousPathGuard` |
| Rewriting the same file repeatedly | `LoopGuard` |
| Leaking keys in params or replies | `SecretLeakGuard` |
| Saying "done" without proof | `UnverifiedCompletionGuard` |
| Sending to the wrong recipient | custom recipient allowlist contract |
| Publishing private identity details | custom outbound identity/dox contract |
| Running production SQL without approval | custom environment + change-ticket contract |
| Declaring blocked after one failed route | custom evidence-before-blocker contract |

The default contracts are intentionally small. The highest-value contracts in a
real system are usually the ones only your runtime can know how to enforce.

## 5. Add tests before trusting the gate

Every contract needs two tests: one that blocks and one that passes.

```python
def test_prod_sql_requires_ticket():
    guard = ProdDatabaseWriteGuard()
    ctx = ActionContext(
        action="tool_call",
        tool="run_sql",
        params={"query": "delete from users"},
        metadata={"environment": "prod"},
    )
    assert guard.check_pre(ctx).blocking


def test_non_prod_sql_passes_without_ticket():
    guard = ProdDatabaseWriteGuard()
    ctx = ActionContext(
        action="tool_call",
        tool="run_sql",
        params={"query": "delete from users"},
        metadata={"environment": "dev"},
    )
    assert guard.check_pre(ctx) is None
```

If a contract has no tests, it is a hope, not a boundary.

## 6. The adoption rule

Do not start by modeling every possible failure. Start with one irreversible or
high-blast-radius action and put a deterministic gate directly in front of it.

Good first targets:

- public publishing
- external email sends
- production database mutations
- shell commands
- filesystem writes outside the workspace
- credential-bearing tool calls

One hard gate in front of one real side effect beats a broad safety framework that
lives only in prompt text.
