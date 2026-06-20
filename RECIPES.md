# Contract recipes

Copy these into your runtime and tighten them around your own tool names,
metadata fields, and escalation paths.

The pattern is always the same:

1. Convert the intended action into an `ActionContext`.
2. Put the facts the contract needs in `tool`, `params`, and `metadata`.
3. Return a `Violation` before the side effect happens.
4. Test one blocked case and one allowed case.

## 1. External email recipient guard

Use when an agent can send email, Slack DMs, support replies, calendar invites, or
anything else to a human outside your system.

```python
from agent_contracts import ActionContext, Contract


class RecipientAllowlistGuard(Contract):
    name = "recipient-allowlist-guard"

    def __init__(self, allowed_domains):
        self.allowed_domains = set(allowed_domains)

    def check_pre(self, ctx: ActionContext):
        if ctx.tool != "send_email":
            return None

        recipients = ctx.params.get("to", [])
        if isinstance(recipients, str):
            recipients = [recipients]

        blocked = [
            recipient
            for recipient in recipients
            if recipient.rsplit("@", 1)[-1] not in self.allowed_domains
        ]
        if blocked:
            return self._violation(
                f"email recipient outside allowlist: {', '.join(blocked)}",
                recovery="Draft the email for review or route through an approved outreach workflow.",
            )
        return None
```

Test shape:

```python
def test_blocks_external_recipient():
    guard = RecipientAllowlistGuard({"example.com"})
    violation = guard.check_pre(
        ActionContext(action="tool_call", tool="send_email", params={"to": "buyer@gmail.com"})
    )
    assert violation.blocking
```

## 2. Production SQL mutation guard

Use when an agent can query a database but should not mutate production without a
ticket, approval id, or deployment gate.

```python
import re

from agent_contracts import ActionContext, Contract


class ProdSqlMutationGuard(Contract):
    name = "prod-sql-mutation-guard"

    _MUTATION = re.compile(r"\b(insert|update|delete|drop|alter|truncate|create)\b", re.I)

    def check_pre(self, ctx: ActionContext):
        if ctx.tool != "run_sql":
            return None
        if ctx.metadata.get("environment") != "prod":
            return None

        query = ctx.params.get("query", "")
        if self._MUTATION.search(query) and not ctx.metadata.get("change_ticket"):
            return self._violation(
                "production SQL mutation requires change_ticket metadata",
                recovery="Attach the approved change ticket or run against a non-production database.",
            )
        return None
```

Test shape:

```python
def test_prod_delete_requires_ticket():
    guard = ProdSqlMutationGuard()
    violation = guard.check_pre(
        ActionContext(
            action="tool_call",
            tool="run_sql",
            params={"query": "delete from users where id = 1"},
            metadata={"environment": "prod"},
        )
    )
    assert violation.blocking
```

## 3. Evidence-before-blocker guard

Use when an agent is allowed to say "blocked" only after it has tried the known
safe recovery paths. This is a post gate because the failure is in the final
claim, not the tool call itself.

```python
import re

from agent_contracts import ActionContext, Contract


class EvidenceBeforeBlockerGuard(Contract):
    name = "evidence-before-blocker-guard"

    _BLOCKED = re.compile(r"\b(blocked|can't|cannot|unable)\b", re.I)

    def __init__(self, required_tools):
        self.required_tools = set(required_tools)

    def check_post(self, ctx: ActionContext):
        if not self._BLOCKED.search(ctx.response_text):
            return None

        tried = set(ctx.tool_calls)
        missing = sorted(self.required_tools - tried)
        if missing:
            return self._violation(
                f"blocker claim before trying required recovery paths: {', '.join(missing)}",
                recovery="Try the missing recovery path or report exactly why it cannot be attempted.",
            )
        return None
```

Test shape:

```python
def test_blocker_claim_requires_recovery_attempts():
    guard = EvidenceBeforeBlockerGuard({"credential_lookup", "browser_retry"})
    violation = guard.check_post(
        ActionContext(
            action="respond",
            response_text="I cannot access the account.",
            tool_calls=["credential_lookup"],
        )
    )
    assert violation.blocking
```

## 4. Public publishing identity guard

Use when the agent can publish on a public account and must not leak private
identity details, internal aliases, or the wrong persona.

```python
from agent_contracts import ActionContext, Contract


class PublicIdentityGuard(Contract):
    name = "public-identity-guard"

    def __init__(self, forbidden_terms):
        self.forbidden_terms = [term.lower() for term in forbidden_terms]

    def check_pre(self, ctx: ActionContext):
        if ctx.tool not in {"publish_post", "send_tweet", "publish_note"}:
            return None

        text = str(ctx.params.get("text") or ctx.params.get("body") or "")
        lowered = text.lower()
        hits = [term for term in self.forbidden_terms if term in lowered]
        if hits:
            return self._violation(
                f"public post contains forbidden identity term(s): {', '.join(hits)}",
                recovery="Remove private identifiers or route through manual review.",
            )
        return None
```

Test shape:

```python
def test_public_post_blocks_private_identifier():
    guard = PublicIdentityGuard({"internal-codename"})
    violation = guard.check_pre(
        ActionContext(
            action="tool_call",
            tool="publish_post",
            params={"text": "Shipping the internal-codename system today."},
        )
    )
    assert violation.blocking
```

## Adoption order

Start with the side effect that can hurt you fastest:

1. Shell commands and file writes.
2. External sends and public publishing.
3. Production database mutations.
4. Payment, account, and infrastructure changes.
5. Completion and blocker claims.

Do not start by modeling every possible behavior. Put one deterministic gate in
front of one real side effect, then repeat.
