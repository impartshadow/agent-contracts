# Changelog

## Unreleased

## 0.1.2 - 2026-06-21

Release notes: [docs/releases/v0.1.2.md](docs/releases/v0.1.2.md)

### Added

- `agent-contracts score` for reproducible 0-100 agent reliability scoring and
  README badge output.
- `agent-contracts score --output-json`, `--output-markdown`, and
  `--output-badge-json` for durable public scorecard artifacts.
- Seed `LEADERBOARD.md` for the Shadow Agent Reliability Index.
- Dogfood policy, scaffold adapter, pre-commit hooks, and GitHub Actions
  workflow for scoring this repository itself.

### Verified

- Current local suite: `PYTHONPATH=. pytest -q` -> `72 passed`.
- Current score: `agent-contracts score --root . --eval examples/eval_corpus.jsonl --replay examples/actions.jsonl` -> `95/100`.

## 0.1.1 - 2026-06-20

Release notes: [docs/releases/v0.1.1.md](docs/releases/v0.1.1.md)

### Added

- Browser playground under `docs/playground/` that runs the real contract engine
  via Pyodide.
- `agent-contracts eval` for labeled JSONL corpora, with true positives, true
  negatives, false positives, false negatives, precision, recall, and expected
  contract misses.
- `agent-contracts doctor` for read-only adoption diagnostics over policy,
  scaffold adapter, GitHub Actions wiring, matrix status, and optional eval
  corpus.
- `WorkspacePathGuard` for blocking file actions that resolve outside a
  configured workspace root.
- `FRAMEWORK_ADAPTERS.md` with adapter patterns for OpenAI tool calls,
  LangChain-style wrappers, AutoGen-style function maps, CrewAI-style tools, raw
  CLI agents, and response-boundary checks.
- Demo console script: `agent-contracts-demo`.
- Shell command guard for common high-blast-radius commands such as `sudo`,
  root recursive deletes, filesystem formatting, raw disk writes, and protected
  redirects.
- JSON serialization for `Violation` and `CheckResult` via `to_dict()`.
- `RECIPES.md` with copy-paste custom contracts for recipient allowlists,
  production SQL mutation gates, evidence-before-blocker checks, and public
  identity gates.
- `THREAT_MODEL.md`, `SECURITY.md`, `CONTRIBUTING.md`, issue templates,
  `AUDIT_CHECKLIST.md`, `COMPARISON.md`, and `FAILURE_MODES.md`.
- `agent-contracts bootstrap` to scaffold a full repository adoption path:
  policy file, GitHub Actions workflow, importable adapter, and local README.
- `agent-contracts replay` to run JSONL action logs through the same pre/post
  gates used by live tool dispatch.
- Replay expectation flags: `--expect-blocks` and `--expect-violations` for
  CI-friendly incident fixtures.
- Replay SARIF output via `agent-contracts replay --sarif`.
- `agent-contracts bootstrap` now writes optional local pre-commit hooks for
  `agent-contracts matrix` and `agent-contracts doctor --root .`.

### Changed

- README now routes users by intent: quickstart, integration patterns,
  framework adapters, audit checklist, recipes, comparison, threat model, and
  contribution/security paths.
- Quickstart now includes framework adapter routing and demo commands.

### Verified

- Current local suite: `PYTHONPATH=. pytest -q` -> `67 passed`.
- Current compile check: `python3 -m compileall -q agent_contracts`.
