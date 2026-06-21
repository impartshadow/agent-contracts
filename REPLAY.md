# Replay

`agent-contracts replay` runs captured action logs through the same registry you
use at runtime. This is the bridge from "added a guard" to "the guard would have
blocked the incident actually seen."

## JSONL Format

Each line is one JSON object. Blank lines and lines starting with `#` are ignored.

```jsonl
{"phase":"pre","action":"tool_call","tool":"write_file","params":{"path":"/etc/passwd"}}
{"phase":"post","action":"respond","response_text":"Done, fixed it."}
```

Supported fields map directly to `ActionContext`:

| Field | Meaning |
|---|---|
| `phase` | `pre` or `post`; defaults to `pre` |
| `action` | Action name, for example `tool_call` or `respond` |
| `tool` | Tool name for pre-action checks |
| `params` | Tool/action parameters |
| `response_text` | Outgoing agent text for post-action checks |
| `user_message` | User request that triggered the action |
| `files_written` | Paths written during the turn |
| `tool_calls` | Tool names called during the turn |
| `edits_by_path` | Edit count by path |
| `metadata` | Application-specific context |

## Run It

Use the default contracts:

```bash
agent-contracts replay examples/actions.jsonl
```

Use a repository policy:

```bash
agent-contracts replay actions.jsonl --policy agent-contracts.yml
```

Emit machine-readable output:

```bash
agent-contracts replay actions.jsonl --json
```

Emit SARIF for GitHub code scanning or security dashboards:

```bash
agent-contracts replay actions.jsonl --sarif > agent-contracts.sarif
```

Assert an incident fixture still blocks:

```bash
agent-contracts replay actions.jsonl --expect-blocks 1
```

Assert total fired violations:

```bash
agent-contracts replay actions.jsonl --expect-violations 2
```

Exit codes:

| Code | Meaning |
|---|---|
| `0` | No blocking violations fired, or expectation flags matched |
| `1` | At least one blocking violation fired |
| `2` | The input file is invalid |

Warnings do not make the command exit non-zero. That lets completion-evidence
warnings show up in logs without failing CI unless you promote them in your own
policy.

## CI Pattern

Keep one small incident fixture in the repository:

```bash
agent-contracts replay tests/fixtures/agent-actions.jsonl --policy agent-contracts.yml --expect-blocks 1
```

When a new failure mode appears, add the minimal action record that reproduces
it. The fixture becomes a regression test for the tool boundary, not a prompt
note future agents can ignore.
