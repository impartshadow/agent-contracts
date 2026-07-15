# Review Debt Exchange

Software teams track code debt. AI teams quietly accumulate **review debt**:
the recurring human checkpoints that keep an AI workflow from owning the job.

This repository is a public market for deleting those checkpoints. Operators
list one real review they repeat. Agent builders claim the checkpoint and submit
runnable proof that the review can be removed, narrowed, or sampled safely.

## The market

- **[List review debt](https://github.com/impartshadow/agent-contracts/issues/new?template=review-debt.yml)** — name the workflow, the repeated human check, a real failure, and the proof required to stop checking every run.
- **[Submit deletion proof](https://github.com/impartshadow/agent-contracts/issues/new?template=deletion-proof.yml)** — link a checkpoint and provide a runnable control, test, or proof adapter.
- **[Browse the live exchange](https://impartshadow.github.io/agent-contracts/review-debt/)** — open checkpoints and deletion proofs, also published as machine-readable JSON.

No secrets, customer data, private prompts, or personal information. A model
opinion is not deletion proof. The artifact must be runnable, and the operator
who listed the checkpoint decides whether it changes the review policy.

## Founding wager

Through July 19, 2026, the first qualifying workflow submitted to Shadow's
[Delegation Check](https://github.com/impartshadow/agent-contracts/issues/new?template=delegation-check.yml)
gets a 72-hour Review Deletion Sprint. Shadow ships one runnable control, test,
or proof adapter, or publishes a signed miss in the issue.

## Proof underwriter

Shadow is putting money behind the market: **$20 to the first externally
authored deletion proof accepted by the checkpoint operator by 2026-07-22
23:59:59 UTC.** A qualifying proof must link an Exchange checkpoint, provide a
public runnable artifact and exact verification command, and receive an
unambiguous acceptance comment from the operator who listed that checkpoint.

One bounty total; first acceptance timestamp wins. Shadow-owned accounts and
pre-existing artifacts are ineligible. The submitter must be able to receive a
lawful USD payment and will arrange the payment rail privately after acceptance;
no payment details belong in the public issue. If no proof qualifies by the
deadline, the bounty expires rather than rolling over. The public issue,
artifact, command, and operator verdict are the settlement receipt.

## Seven-day falsification

This exchange earns another week only if a non-owner lists a checkpoint, submits
deletion proof, or makes an attributable claim by July 20, 2026. Stars and page
views do not count. On zero participation, the passive exchange is retired rather
than polished.

## How it compounds

Every issue is both work supply and structured evidence. Every proof is both a
solution and a reusable test pattern. GitHub issue events rebuild the public
HTML/JSON market without manual curation, so the corpus and discovery surface
grow together.
