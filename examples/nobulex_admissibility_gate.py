"""Admissibility gate for Nobulex @track — delegation check artifact.

Nobulex 0.1.0 receipts prove what happened. This gate makes them also prove
what was *allowed* to happen, using fields the Receipt schema already signs
(verdict, policy_version) but the @track decorator never populates.

Three properties, per the falsification tests circulating in the autogen thread:
1. Policy evaluates BEFORE the side effect fires (in @track it fires after).
2. Fail closed: unparseable/unknown input -> signed DENY receipt, no execution.
3. Deterministic: same denied call twice -> same DENY verdict, reproducible.

Run: python nobulex_admissibility_gate.py
"""

import functools
import hashlib
import json

from nobulex.agent import Agent


def _policy_hash(policy: dict) -> str:
    return hashlib.sha256(
        json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


class Refused(Exception):
    def __init__(self, receipt):
        self.receipt = receipt
        super().__init__(f"refused: {receipt.scope}")


def guard(agent_id: str, policy: dict):
    """Pre-condition gate. Evaluates policy before calling func.

    policy = {"max_amount": 500, "allowed_currencies": ["USD"]}
    The policy decision is signed into the receipt (verdict + policy_version),
    so an auditor can verify authorization offline, not just occurrence.
    """
    agent = Agent(agent_id)
    pv = f"policy-sha256:{_policy_hash(policy)}"

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            scope = f"args:{str(args)[:80]} kwargs:{str(kwargs)[:80]}"
            # ---- admissibility check: BEFORE the side effect ----
            try:
                amount = kwargs.get("amount", args[1] if len(args) > 1 else None)
                currency = kwargs.get("currency", "USD")
                admissible = (
                    isinstance(amount, (int, float))
                    and amount <= policy["max_amount"]
                    and currency in policy["allowed_currencies"]
                )
            except Exception:
                admissible = False  # fail closed on anything unparseable

            if not admissible:
                # escalation receipt: signed DENY, side effect never ran
                r = agent.deny(func.__name__, scope=scope,
                               metadata={"policy_version": pv,
                                         "escalate_to": "human"})
                raise Refused(r)

            result = func(*args, **kwargs)  # side effect fires only if allowed
            r = agent.act(func.__name__, scope=scope, verdict="ALLOW",
                          metadata={"policy_version": pv})
            wrapper.last_receipt = r
            return result

        wrapper.agent = agent
        return wrapper

    return decorator


# ---- demo: the send_payment example from the thread ----

PAYMENTS_SENT = []


@guard("payments-bot", {"max_amount": 500, "allowed_currencies": ["USD"]})
def send_payment(to: str, amount: float, currency: str = "USD"):
    PAYMENTS_SENT.append((to, amount, currency))
    return f"paid {to} {amount} {currency}"


if __name__ == "__main__":
    # 1. allowed call -> ALLOW receipt with policy_version in signed preimage
    print(send_payment("vendor-a", 120.0))
    r = send_payment.last_receipt
    print("verdict:", r.verdict, "| policy:", r.metadata.get("policy_version"),
          "| sig verifies:", r.verify())

    # 2. over-budget -> signed DENY, side effect never fired
    for attempt in (1, 2):  # run twice: deterministic DENY both times
        try:
            send_payment("vendor-b", 9_000.0)
        except Refused as e:
            print(f"denied (attempt {attempt}):", e.receipt.verdict,
                  "| escalate:", e.receipt.metadata.get("escalate_to"),
                  "| sig verifies:", e.receipt.verify())

    # 3. unparseable amount -> fail closed
    try:
        send_payment("vendor-c", "ALL OF IT")
    except Refused as e:
        print("fail-closed:", e.receipt.verdict, "| sig verifies:", e.receipt.verify())

    print("payments actually sent:", PAYMENTS_SENT)
    assert PAYMENTS_SENT == [("vendor-a", 120.0, "USD")]
    print("OK — only the admissible call crossed the boundary")
