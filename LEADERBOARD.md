# Shadow Agent Reliability Index

This is the seed format for public scoring. A score is not a vibes-based review;
it is the output of `agent-contracts score` against an agent repository.

| Rank | Project | Score | Evidence |
|---:|---|---:|---|
| 1 | `impartshadow/agent-contracts` | 95/100 | `agent-contracts score --root . --eval examples/eval_corpus.jsonl --replay examples/actions.jsonl` |

## How to Submit

Open an issue or PR with:

- Repository URL
- `agent-contracts score --json` output, if already wired
- Any JSONL incident replay or labeled eval corpus the project wants scored

Minimum bar for the public table:

- A policy file exists
- The built-in contract matrix passes
- The score output is reproducible from CI or a clean clone

Scores are intentionally harsh. Missing eval and replay data stays at zero
instead of receiving credit for a story about what the agent probably does.
