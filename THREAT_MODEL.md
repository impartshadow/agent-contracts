# Threat Model

`agent-contracts` is a deterministic action gate for LLM agents. It is not a
sandbox, permission system, policy engine, or replacement for normal application
security. Use it to stop known-bad agent actions before they reach your tools.

## Protects

The library is designed for failures at the agent/tool boundary:

| Threat | Example | Guard shape |
|---|---|---|
| Dangerous side effects | Agent writes to `/etc/passwd` or `.ssh/config` | Pre-action path contract |
| Secret exfiltration | Agent sends an API key in tool args or final text | Pre/post regex contract |
| Runaway loops | Agent rewrites the same file repeatedly | Per-turn state contract |
| Authority drift | Research agent tries to send email or deploy | Tool allowlist contract |
| False completion claims | Agent says "shipped" without a hash, path, URL, or output | Post-action evidence contract |

These checks work best when they run in the shared tool router, API client, or
orchestrator layer. A contract that only appears in the prompt is not a contract.

## Does Not Protect

`agent-contracts` does not defend against:

- Code execution inside a tool after the tool has been allowed.
- Filesystem or network access outside the process where you run the contracts.
- Prompt injection in retrieved documents unless you write a contract for that
  specific behavior.
- A malicious host application that ignores `BlockedAction`.
- Secrets already loaded into model context before a contract sees the action.
- Semantic judgments that require business context, legal review, or human taste.

For those, use OS sandboxing, least-privilege credentials, scoped API tokens,
network egress controls, human review, and normal app authorization.

## Trust Boundary

The trust boundary is the point where model output becomes a side effect:

```text
model proposes action -> ActionContext -> Registry.enforce_pre -> real tool call
```

If a tool can mutate state, spend money, send messages, publish content, trade,
delete data, or call another service, put the contract gate immediately before
that tool executes. Do not rely on the model to remember the rule.

For outgoing text, run the post gate before the response leaves your runtime:

```text
model drafts response -> ActionContext(response_text=...) -> Registry.check_post -> user/channel
```

## Deployment Rules

Use these as defaults:

1. Put contracts in code, not only in prompts.
2. Fail closed for `BLOCK` violations.
3. Log all violations with the contract name, action, tool, and recovery text.
4. Keep credentials out of model context; contracts are a backstop, not storage.
5. Use role-specific tool allowlists for every autonomous agent role.
6. Write one custom contract for every production incident you never want twice.

## Good Custom Contracts

Good contracts are narrow, boring, and testable:

```python
class NoExternalEmailWithoutRecipientApproval(Contract):
    name = "approved-recipient-guard"

    def check_pre(self, ctx):
        if ctx.tool != "send_email":
            return None
        recipient = ctx.params.get("to", "")
        approved = ctx.metadata.get("approved_recipients", set())
        if recipient not in approved:
            return self._violation(
                f"email recipient {recipient!r} is not approved",
                recovery="Queue the draft for review or request explicit approval.",
            )
        return None
```

Weak contracts try to solve taste, strategy, or broad ethics. Strong contracts
encode an operational line that should never move.
