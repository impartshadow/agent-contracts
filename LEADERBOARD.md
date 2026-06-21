# Shadow Agent Governance Index

A public, mechanical scorecard for autonomous-agent repositories.
Every score is the output of `agent-contracts scan` against a clean clone —
no vibes, no testimonials. The scanner reads observable governance *surface*
(tests/CI, tool gating, secret hygiene, dependency pinning, eval harness,
observability, resilience). It does not claim the agent is safe at runtime;
it measures whether the guardrails a reliable agent needs are present.

Scores are intentionally harsh. A missing dimension earns zero — there is no
credit for a story about what the agent probably does.

| Rank | Project | Score | Grade | Strongest | Weakest |
|---:|---|---:|:--:|---|---|
| 1 | [`langchain-ai/langgraph`](https://github.com/langchain-ai/langgraph) | 100/100 | A | tests_and_ci | tests_and_ci |
| 2 | [`microsoft/autogen`](https://github.com/microsoft/autogen) | 100/100 | A | tests_and_ci | tests_and_ci |
| 3 | [`Significant-Gravitas/AutoGPT`](https://github.com/Significant-Gravitas/AutoGPT) | 93/100 | A | tests_and_ci | secret_safety |
| 4 | [`All-Hands-AI/OpenHands`](https://github.com/All-Hands-AI/OpenHands) | 93/100 | A | tests_and_ci | secret_safety |
| 5 | [`geekan/MetaGPT`](https://github.com/geekan/MetaGPT) | 90/100 | A | tests_and_ci | secret_safety |
| 6 | [`crewAIInc/crewAI`](https://github.com/crewAIInc/crewAI) | 85/100 | B | tests_and_ci | dependency_pinning |
| 7 | [`openai/swarm`](https://github.com/openai/swarm) | 70/100 | C | tool_governance | dependency_pinning |
| 8 | [`yoheinakajima/babyagi`](https://github.com/yoheinakajima/babyagi) | 65/100 | D | tool_governance | tests_and_ci |

## Reproduce any score

```bash
pip install agent-contracts
git clone --depth 1 https://github.com/<owner>/<repo>.git
agent-contracts scan --root <repo> --json
```

## Submit your agent

Run the scanner against your repo and open a PR with the score row:

```bash
pip install agent-contracts
agent-contracts scan --root . --output-markdown AGENT_GOVERNANCE_SCORE.md --json
```

Self-scores are accepted only when reproducible from a clean clone.
Open an issue with your repo URL to request an independent score.

## Want a full contract audit?

The leaderboard measures *governance surface* — the observable layer.
A full audit goes one level deeper: which of your agent's actual failure modes are
uncontracted, which contracts fire on your real action traces, and which gaps are
highest-risk given your deployment context.

**[Request a contract audit →](https://echofromshadow.substack.com)** — $299 flat, delivered as a signed AGENT_AUDIT.md in your repo with reproducible evidence for every finding.

## Dimensions (100 points)

| Dimension | Max | What it checks |
|---|---:|---|
| tests_and_ci | 20 | a test suite plus CI that runs it |
| tool_governance | 20 | permission/allowlist/approval/human-in-loop gating |
| secret_safety | 15 | secrets git-ignored, no obvious hardcoded keys |
| dependency_pinning | 10 | a lockfile or pinned dependency manifest |
| eval_harness | 15 | an eval / benchmark / labeled-corpus surface |
| observability | 10 | logging / audit / tracing |
| resilience | 10 | retry / backoff / fallback / escalation |
