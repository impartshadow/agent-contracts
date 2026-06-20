# Changelog

## Unreleased

### Added

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

### Changed

- README now routes users by intent: quickstart, integration patterns,
  framework adapters, audit checklist, recipes, comparison, threat model, and
  contribution/security paths.
- Quickstart now includes framework adapter routing and demo commands.

### Verified

- Current local suite: `PYTHONPATH=. pytest -q` -> `31 passed`.
- Current compile check: `python3 -m compileall -q agent_contracts`.

