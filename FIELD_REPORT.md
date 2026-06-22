# Field Report: 2,292 caught failures in 30 days

This is the operator's-eye companion to [FAILURE_MODES.md](FAILURE_MODES.md) and [CONTRACT_MATRIX.md](CONTRACT_MATRIX.md). FAILURE_MODES is the taxonomy; this is what the taxonomy looked like in production over a single 30-day window (May 22 – Jun 21), pulled straight from the live violation ledger of one autonomous agent running a real business.

## What the contracts caught

| Catches (30d) | Failure mode | What it actually is |
|---|---|---|
| 659 | persistent-correction | The agent repeats a behavior the operator already told it to stop |
| 293 | decision-verification | A claim or decision asserted without the evidence that backs it |
| 259 | auth-fallback-skipped | Surfaces a blocker to the human before trying the route that works |
| 194 | factual-claim-verification | A definitive statement that was never actually checked |
| 190 | explain-instead-of-act | Describes the action instead of taking it |
| 153 | edit-loop | Thrashes on the same file, committing the same area over and over |
| 115 | wrong-tool-route | Reaches for a slow/expensive tool when a canonical path exists |
| 82  | dox-leak | Personal identifiers headed into an outbound channel |

**Total: 2,292 catches before anything reached the outside world.**

## The one lesson

The biggest category by a wide margin — 659 catches, nearly a third — is the agent regenerating a behavior it was *already corrected on*. That's not a knowledge gap, it's a persistence gap, and it's invisible to better base models because it lives between the model and the world, not inside it.

Prose rules don't hold it. A sentence in a prompt is a suggestion competing with everything else in context; the model regenerates the bad behavior from upstream faster than the rule can suppress it. What holds is a deterministic contract that inspects the proposed action or drafted response and blocks, rewrites, or flags it *before* it ships. Detect the class, write the contract, let the prose retire to documentation.

The counterintuitive payoff: governance is what lets you *increase* an agent's authority. Because the dangerous classes are caught deterministically, the operator can hand the agent standing permission to push code, send email, and publish — the blast radius is bounded by the gates, not by supervision. An autonomous agent earns more autonomy in exact proportion to how well its failure classes are governed.

## The full write-up

The narrative version of this report — written by the agent's operator — is published here: **[echofromshadow.substack.com](https://echofromshadow.substack.com)**.

*The numbers above are real, not a thought experiment. They're the actual contract-catch counts from 30 days of a production agent's ledger.*
