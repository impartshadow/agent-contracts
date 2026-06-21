# Distribution pack

Use these when sharing `agent-contracts` with engineers who run agent loops,
tool routers, MCP gateways, or eval harnesses. The point is not "AI safety" in
general. The point is one deterministic gate before one side effect.

## Primary links

- Live browser proof: https://impartshadow.github.io/agent-contracts/playground/
- First 10 minutes: https://github.com/impartshadow/agent-contracts/blob/main/FIRST_10_MINUTES.md
- Repository: https://github.com/impartshadow/agent-contracts
- Failure taxonomy: https://github.com/impartshadow/agent-contracts/blob/main/FAILURE_MODES.md
- Comparison: https://github.com/impartshadow/agent-contracts/blob/main/COMPARISON.md

## Short post

Most agent guardrails ask a second model to judge the first model.

That is the wrong boundary for tool use.

If an agent is about to write `/etc/passwd`, leak an API key, or claim "done"
with no evidence, the gate should be deterministic: regexes, path checks,
allowlists, and tests.

I built `agent-contracts`: pre/post-condition contracts for agent actions. No
model in the loop, zero runtime deps, MIT.

Try the live browser proof:
https://impartshadow.github.io/agent-contracts/playground/

## Technical post

The useful agent-safety primitive is not a better prompt. It is a shared
side-effect boundary.

Every tool call should pass through a deterministic precondition check before it
touches disk, shell, email, Slack, prod data, or public publishing. Every final
response should pass through a deterministic postcondition check before it leaves
the runtime.

That catches the failures prompts cannot reliably prevent:

- writes outside the workspace
- destructive shell commands
- leaked tokens
- unapproved recipients
- repeated edit loops
- "done" claims with no evidence

`agent-contracts` is the extracted version of that layer. Plain Python contracts,
CLI checks, replay against action logs, SARIF output, CI scaffold, and a browser
playground running the real engine via Pyodide.

Start here:
https://github.com/impartshadow/agent-contracts/blob/main/FIRST_10_MINUTES.md

## Contrarian post

"LLM-as-judge" is useful for taste, ranking, and fuzzy evaluation.

It is a weak mechanism for hard operational boundaries.

When a system path, production table, outbound recipient, API key, or public
identity is involved, the correct question is not "does another model think this
looks safe?"

The question is "does this action satisfy the contract?"

That answer should be deterministic, unit-tested, and cheap enough to run on
every tool call.

`agent-contracts` is that layer:
https://github.com/impartshadow/agent-contracts

## Hacker News / Reddit framing

I extracted the deterministic contract layer from my own agent runtime into a
small MIT Python package.

It wraps preconditions around tool calls and postconditions around responses:
workspace path checks, destructive shell checks, secret leaks, loop detection,
completion-claim evidence, role/tool allowlists, replay, SARIF, and CI scaffold.

The design bias is intentionally boring: no model call, no policy prompt, no
runtime dependency. A contract is a Python function over an action context. If it
blocks, the side effect never runs.

Live browser playground:
https://impartshadow.github.io/agent-contracts/playground/

Repo:
https://github.com/impartshadow/agent-contracts

## Reply snippets

**If someone says this is just regexes:**

Yes. That is the point for hard boundaries. I want `rm -rf /`, `/etc/passwd`,
AWS keys, and unapproved recipients caught by deterministic checks, not by a
second stochastic reviewer.

**If someone asks how this differs from Guardrails AI / NeMo:**

Those are broader policy/dialogue frameworks. This is narrower: one deterministic
gate before side effects and one after responses. The comparison doc is explicit
about when to use the other tools instead.

**If someone asks where to wire it:**

In the shared dispatcher/client for the side effect, not the prompt. If shell,
browser automation, helper scripts, and direct API calls can all mutate the same
thing, the contract belongs below those paths.

**If someone asks whether this is a sandbox:**

No. It is an action gate. It reduces classes of bad calls before execution, but
it does not replace OS permissions, network policy, container isolation, or human
review for irreversible changes.

