# Agent Governance Index — Change Report

Run `2026-08-17T03:31:24Z` vs previous `2026-08-10T03:31:20Z`

**2 regressions · 0 improvements · 0 new · 25 unchanged**

## Regressions

| Project | Score | Grade | What dropped | Scanned commit |
|---|---:|:--:|---|---|
| [`letta-ai/letta`](https://github.com/letta-ai/letta) | 78→20 (-58) | C→F | dependency_pinning 10→0; observability 10→0; resilience 10→0; secret_safety 8→7; tests_and_ci 20→0; tool_governance 20→13 | `87fd37aab6` |
| [`microsoft/semantic-kernel`](https://github.com/microsoft/semantic-kernel) | 100→93 (-7) | A | secret_safety 15→8 | `c028a0c7dc` |

---

Every score is reproducible: `agent-contracts scan --root <clone>` at the recorded commit. This report is generated mechanically from `leaderboard_history.jsonl`.
