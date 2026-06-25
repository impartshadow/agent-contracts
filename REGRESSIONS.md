# Agent Governance Index — Change Report

Run `2026-06-25T13:09:18Z` vs previous `2026-06-24T11:03:37Z`

**1 regressions · 1 improvements · 0 new · 25 unchanged**

## Regressions

| Project | Score | Grade | What dropped | Scanned commit |
|---|---:|:--:|---|---|
| [`crewAIInc/crewAI`](https://github.com/crewAIInc/crewAI) | 85→93 (+8) | B→A | dependency_pinning 0→10; observability 5→10; secret_safety 15→8 | `01fc389d4a` |

## Improvements

- `run-llama/llama_index` 93→100 (+7): secret_safety 8→15

---

Every score is reproducible: `agent-contracts scan --root <clone>` at the recorded commit. This report is generated mechanically from `leaderboard_history.jsonl`.
