# Shadow Agent Governance Index

A public, mechanical scorecard for autonomous-agent repositories.
Every score is the output of `agent-contracts scan` against a clean clone —
no vibes, no testimonials. The scanner reads observable governance *surface*
(tests/CI, tool gating, secret hygiene, dependency pinning, eval harness,
observability, resilience). It does not claim the agent is safe at runtime;
it measures whether the guardrails a reliable agent needs are present.

The **Trend** column is the movement since the previous scan — this index is
re-run on a schedule, so a dropped guardrail shows up here as a regression.

Scores are intentionally harsh. A missing dimension earns zero — there is no
credit for a story about what the agent probably does.

| Rank | Project | Score | Grade | Trend | Strongest | Weakest |
|---:|---|---:|:--:|:--:|---|---|
| 1 | [`langchain-ai/langgraph`](https://github.com/langchain-ai/langgraph) | 100/100 | A | new | tests_and_ci | — |
| 2 | [`microsoft/autogen`](https://github.com/microsoft/autogen) | 100/100 | A | new | tests_and_ci | — |
| 3 | [`run-llama/llama_index`](https://github.com/run-llama/llama_index) | 100/100 | A | new | tests_and_ci | — |
| 4 | [`microsoft/semantic-kernel`](https://github.com/microsoft/semantic-kernel) | 100/100 | A | new | tests_and_ci | — |
| 5 | [`stanfordnlp/dspy`](https://github.com/stanfordnlp/dspy) | 100/100 | A | new | tests_and_ci | — |
| 6 | [`Significant-Gravitas/AutoGPT`](https://github.com/Significant-Gravitas/AutoGPT) | 93/100 | A | – | tests_and_ci | secret_safety |
| 7 | [`crewAIInc/crewAI`](https://github.com/crewAIInc/crewAI) | 93/100 | A | new | tests_and_ci | secret_safety |
| 8 | [`All-Hands-AI/OpenHands`](https://github.com/All-Hands-AI/OpenHands) | 93/100 | A | new | tests_and_ci | secret_safety |
| 9 | [`langchain-ai/langchain`](https://github.com/langchain-ai/langchain) | 93/100 | A | new | tests_and_ci | secret_safety |
| 10 | [`camel-ai/camel`](https://github.com/camel-ai/camel) | 93/100 | A | new | tests_and_ci | secret_safety |
| 11 | [`pydantic/pydantic-ai`](https://github.com/pydantic/pydantic-ai) | 93/100 | A | new | tests_and_ci | secret_safety |
| 12 | [`openai/openai-agents-python`](https://github.com/openai/openai-agents-python) | 93/100 | A | new | tests_and_ci | secret_safety |
| 13 | [`mem0ai/mem0`](https://github.com/mem0ai/mem0) | 93/100 | A | new | tests_and_ci | secret_safety |
| 14 | [`agno-agi/agno`](https://github.com/agno-agi/agno) | 93/100 | A | new | tests_and_ci | secret_safety |
| 15 | [`geekan/MetaGPT`](https://github.com/geekan/MetaGPT) | 90/100 | A | new | tests_and_ci | secret_safety |
| 16 | [`princeton-nlp/SWE-agent`](https://github.com/princeton-nlp/SWE-agent) | 90/100 | A | new | tests_and_ci | dependency_pinning |
| 17 | [`huggingface/smolagents`](https://github.com/huggingface/smolagents) | 90/100 | A | new | tests_and_ci | dependency_pinning |
| 18 | [`google/adk-python`](https://github.com/google/adk-python) | 90/100 | A | new | tests_and_ci | secret_safety |
| 19 | [`assafelovic/gpt-researcher`](https://github.com/assafelovic/gpt-researcher) | 85/100 | B | new | tool_governance | dependency_pinning |
| 20 | [`Aider-AI/aider`](https://github.com/Aider-AI/aider) | 84/100 | B | new | tests_and_ci | secret_safety |
| 21 | [`OpenBMB/ChatDev`](https://github.com/OpenBMB/ChatDev) | 80/100 | B | new | tool_governance | eval_harness |
| 22 | [`TransformerOptimus/SuperAGI`](https://github.com/TransformerOptimus/SuperAGI) | 78/100 | C | new | tests_and_ci | eval_harness |
| 23 | [`letta-ai/letta`](https://github.com/letta-ai/letta) | 78/100 | C | new | tests_and_ci | eval_harness |
| 24 | [`reworkd/AgentGPT`](https://github.com/reworkd/AgentGPT) | 78/100 | C | new | tests_and_ci | eval_harness |
| 25 | [`openai/swarm`](https://github.com/openai/swarm) | 70/100 | C | – | tool_governance | dependency_pinning |
| 26 | [`yoheinakajima/babyagi`](https://github.com/yoheinakajima/babyagi) | 65/100 | D | – | tool_governance | tests_and_ci |
| 27 | [`microsoft/JARVIS`](https://github.com/microsoft/JARVIS) | 65/100 | D | new | secret_safety | tests_and_ci |

## Reproduce any score

```bash
pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"
git clone --depth 1 https://github.com/<owner>/<repo>.git
agent-contracts scan --root <repo> --json
```

## Submit your agent

Open an issue with your repo URL, or run `agent-contracts scan --root . --output-markdown AGENT_GOVERNANCE_SCORE.md` and open a PR adding the row.
Self-scores are accepted only when reproducible from a clean clone.

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
