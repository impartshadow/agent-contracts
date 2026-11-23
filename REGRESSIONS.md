# Agent Governance Index — Change Report

Run `2026-11-23T03:31:44Z` vs previous `2026-11-16T03:31:45Z`

**1 regressions · 1 improvements · 0 new · 25 unchanged**

## Regressions

| Project | Score | Grade | What dropped | Scanned commit |
|---|---:|:--:|---|---|
| [`huggingface/smolagents`](https://github.com/huggingface/smolagents) | 90→83 (-7) | A→B | secret_safety 15→8 | `99721bdc3b` |

## Improvements

- `assafelovic/gpt-researcher` 90→100 (+10): dependency_pinning 0→10

---

Every score is reproducible: `agent-contracts scan --root <clone>` at the recorded commit. This report is generated mechanically from `leaderboard_history.jsonl`.
