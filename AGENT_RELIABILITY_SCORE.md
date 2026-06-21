# Agent Reliability Score

**Score: 95/100 (grade A)**

![Agent reliability: 95/100](https://img.shields.io/badge/agent%20reliability-95%2F100-brightgreen)

| Component | Points |
|---|---:|
| adoption_wiring | 40 / 40 |
| built_in_contract_matrix | 20 / 20 |
| labeled_eval_corpus | 25 / 25 |
| incident_replay | 10 / 15 |

This score is mechanical, not a testimonial. It weights adoption wiring,
the built-in contract matrix, labeled eval coverage, and incident replay.
Missing eval or replay data earns zero for that component.

Reproduce:

```bash
agent-contracts score --root . --eval examples/eval_corpus.jsonl --replay examples/actions.jsonl --json
```
