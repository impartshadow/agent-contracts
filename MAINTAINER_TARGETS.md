# Maintainer target queue

This is the execution queue for agent-native distribution. Each target must have
a real contribution angle before contact. A score by itself is not enough.

## Triage rule

Open an issue or PR only when all four are true:

| Check | Bar |
|---|---|
| Reproduced | The current score was reproduced from a clean clone within the last 14 days |
| Specific | The note points to the exact missing governance surface, not a generic grade |
| Useful | The target project would be better even if it never adopts `agent-contracts` |
| Narrow | The request is a docs/example/CI snippet, not a broad safety argument |

Blocked patterns:

- "We scanned you" without a fix path
- ranking-shame comments
- link-only promotion
- opening issues on projects that already score 100/100 unless there is a docs
  integration angle
- claiming the score proves runtime safety

## Priority targets

| Priority | Project | Score | First useful touch | Why this target matters |
|---:|---|---:|---|---|
| 1 | `Aider-AI/aider` | 84 | Docs issue or PR showing a workspace/shell/completion-evidence gate around coding-agent side effects | Coding-agent users understand the pain immediately; score has real room to improve |
| 2 | `crewAIInc/crewAI` | 85 | Example PR: deterministic precondition around crew tools that mutate external state | Productionizing crews is a natural buyer pain; gap is adoption-friction, not awareness |
| 3 | `run-llama/llama_index` | 93 | Docs/example PR for agent tool calls that touch files, HTTP, or retrieval-side effects | Large agent-builder audience; high score makes the approach collaborative rather than accusatory |
| 4 | `All-Hands-AI/OpenHands` | 93 | Issue with a reproducible workspace/shell boundary example for coding agents | Strong fit for hard side-effect gates and public engineering discussion |
| 5 | `huggingface/smolagents` | 90 | CI badge/docs PR showing public governance score generation | Hugging Face ecosystem can spread examples quickly |
| 6 | `pydantic/pydantic-ai` | 93 | Integration note: typed action context + deterministic tool preconditions | Audience values explicit schemas and testable boundaries |
| 7 | `princeton-nlp/SWE-agent` | 90 | Docs issue: completion-claim evidence and workspace write gates for coding tasks | Research credibility plus direct coding-agent relevance |
| 8 | `openai/openai-agents-python` | 93 | Example wrapper around tool execution with pre/post-condition checks | High visibility; must be precise and non-promotional |
| 9 | `microsoft/autogen` | 100 | Discussion/docs-only angle: where contracts sit in multi-agent orchestration | Already scores 100, so do not lead with leaderboard |
| 10 | `langchain-ai/langgraph` | 100 | Discussion/docs-only angle: deterministic side-effect boundary around graph tool nodes | Huge audience, but no issue unless the contribution is clearly additive |

## In-flight

| Date | Target | Touch | Status |
|---|---|---|---|
| 2026-06-23 | `Aider-AI/aider` | PR: ignore `.env` in `.gitignore` to stop committed API keys (the repo's only soft dimension, `secret_safety`, traced to this missing rule) | Open — [PR #5314](https://github.com/Aider-AI/aider/pull/5314) |

## Next moves

1. Reproduce fresh scans for `crewAIInc/crewAI` and `run-llama/llama_index`.
2. For each, inspect the repo docs/examples for the natural tool-execution
   boundary.
3. Draft one concrete docs/example PR or issue per repo, contribution-first.

## Message shape

Use this structure for any maintainer touch:

```text
I ran a reproducible governance scan against <repo> and found one narrow place
where a deterministic gate could help: <specific boundary>.

The issue is not "the project is unsafe"; the scan only measures observable
governance surface. The concrete gap is <dimension> because <evidence>.

Suggested fix: <small docs/example/CI snippet>.

Reproduce:
<commands>
```

The contribution should stand on its own. The leaderboard link is supporting
evidence, not the ask.
