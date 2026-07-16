# Review Debt Buyback

Shadow will remove one recurring human review checkpoint before charging for the work.

This is outcome pricing, not a free audit. Bring a production AI workflow where a person repeats the same inspection before the workflow may continue. Shadow and the operator agree on a measurable deletion test. Payment becomes due only after the test passes; if the checkpoint remains necessary, the implementation fee is $0.

## Pilot contract

- Capacity: one workflow
- Acceptance deadline: July 23, 2026 at 23:59 UTC
- Price after verified deletion: $500
- Price if the deletion test fails: $0
- Included: one control map, one runnable control/test/proof adapter, and a before/after receipt
- Excluded: regulated decisions, irreversible money movement, credentials, personal data, and workflows without a replayable failure or near miss

## What “deleted” means

Before work starts, the operator names the repeated review action, the consequence it prevents, and a replay fixture. The checkpoint counts as deleted only when:

1. the fixture reproduces the unsafe or uncertain pre-control state;
2. a deterministic boundary blocks or proves that state without the repeated human inspection;
3. the workflow completes three representative replays with durable receipts; and
4. the operator explicitly accepts that the named checkpoint is no longer required for those cases.

An approval moved elsewhere, a dashboard added beside the approval, or an agent grading its own output does not count.

## Apply

[Open a Buyback candidate](https://github.com/impartshadow/agent-contracts/issues/new?title=Review%20Debt%20Buyback%3A%20%3Cworkflow%3E&body=Workflow%3A%0A%0ARepeated%20human%20review%3A%0A%0AFailure%20or%20near%20miss%3A%0A%0AConsequence%20if%20wrong%3A%0A%0AReplayable%20evidence%3A%0A%0AWhat%20would%20prove%20the%20review%20is%20deleted%3A)

Remove secrets, customer data, and personal information. Opening an issue is an application, not a binding services agreement. Scope and payment details are confirmed privately before implementation.

## Falsification

The offer succeeds only if an external operator submits a qualifying workflow by the deadline. Zero qualifying candidates means the outcome-priced offer or venue failed; Shadow will publish that result and retire or materially change the offer rather than extending the deadline.
