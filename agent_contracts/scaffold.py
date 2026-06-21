"""Repository bootstrap files for adopting agent-contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from .policy import DEFAULT_POLICY_FILENAME, render_policy


DEFAULT_SCAFFOLD_DIR = "agent_contracts_scaffold"
DEFAULT_WORKFLOW_PATH = ".github/workflows/agent-contracts.yml"
DEFAULT_PRE_COMMIT_PATH = ".pre-commit-config.yaml"


def render_python_adapter(policy_path: str = DEFAULT_POLICY_FILENAME) -> str:
    """Return a small adapter module teams can wire into their tool boundary."""

    return f'''"""Local agent-contracts adapter.

Import these helpers at the shared tool dispatcher boundary. The important rule:
call ``gate_tool_call`` before the side-effecting tool runs, and call
``gate_response`` before text leaves the agent.
"""

from __future__ import annotations

from typing import Optional

from agent_contracts import ActionContext, load_policy


REGISTRY = load_policy("{policy_path}")


def gate_tool_call(
    tool: str,
    params: dict,
    *,
    edits_by_path: Optional[dict[str, int]] = None,
    user_message: str = "",
) -> None:
    """Raise BlockedAction if a tool call violates the local policy."""

    REGISTRY.enforce_pre(
        ActionContext(
            action="tool_call",
            tool=tool,
            params=params,
            edits_by_path=edits_by_path or {{}},
            user_message=user_message,
        )
    )


def gate_response(
    text: str,
    *,
    user_message: str = "",
    tool_calls: Optional[list[str]] = None,
) -> list[dict[str, object]]:
    """Return post-check violations as dictionaries for logs or warnings."""

    result = REGISTRY.check_post(
        ActionContext(
            action="respond",
            response_text=text,
            user_message=user_message,
            tool_calls=tool_calls or [],
        )
    )
    return [violation.to_dict() for violation in result.violations]
'''


def render_github_actions() -> str:
    """Return a GitHub Actions workflow that proves the contract boundary."""

    return """name: agent-contracts

on:
  pull_request:
  push:
    branches: [main]

jobs:
  contract-boundary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"
      - run: agent-contracts matrix
      - run: agent-contracts check-pre --policy agent-contracts.yml --tool write_file --params-json '{"path":"notes.md","content":"ok"}'
      - run: |
          if agent-contracts check-pre --policy agent-contracts.yml --tool write_file --params-json '{"path":"../outside.txt","content":"no"}'; then
            echo "workspace escape unexpectedly passed"
            exit 1
          fi
"""


def render_pre_commit_config() -> str:
    """Return a local pre-commit config that checks the contract boundary."""

    return """repos:
  - repo: local
    hooks:
      - id: agent-contracts-matrix
        name: agent-contracts matrix
        entry: agent-contracts matrix
        language: system
        pass_filenames: false
      - id: agent-contracts-doctor
        name: agent-contracts doctor
        entry: agent-contracts doctor --root .
        language: system
        pass_filenames: false
"""


def render_scaffold_readme(workspace_root: str = ".") -> str:
    """Return instructions for the generated scaffold directory."""

    return f"""# agent-contracts scaffold

Generated files:

- `agent-contracts.yml` - local policy, workspace root `{workspace_root}`
- `.github/workflows/agent-contracts.yml` - CI proof that the built-in matrix and one workspace escape check fire
- `.pre-commit-config.yaml` - optional local hook that runs the matrix and doctor before commits
- `agent_contracts_scaffold/adapter.py` - importable helper for the shared tool dispatcher

Wire the adapter at the one place where your agent dispatches tools:

```python
from agent_contracts_scaffold.adapter import gate_tool_call, gate_response

gate_tool_call(tool_name, tool_params, edits_by_path=edit_counts)
result = run_tool(tool_name, tool_params)
warnings = gate_response(agent_reply, tool_calls=[tool_name])
```

The adoption bar is simple: a blocked tool call must fail before the side effect
runs. If the contract only logs after the tool runs, it is monitoring, not a
boundary.
"""


def _write(target: Path, content: str, *, force: bool, written: list[Path]) -> None:
    if target.exists() and not force:
        raise FileExistsError(f"{target} already exists; pass --force to overwrite")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    written.append(target)


def write_scaffold(
    root: Union[str, Path] = ".",
    *,
    workspace_root: str = ".",
    force: bool = False,
) -> list[Path]:
    """Write a policy, adapter, CI workflow, and local README into ``root``."""

    base = Path(root)
    written: list[Path] = []
    _write(base / DEFAULT_POLICY_FILENAME, render_policy(workspace_root), force=force, written=written)
    _write(base / DEFAULT_WORKFLOW_PATH, render_github_actions(), force=force, written=written)
    _write(base / DEFAULT_PRE_COMMIT_PATH, render_pre_commit_config(), force=force, written=written)
    _write(
        base / DEFAULT_SCAFFOLD_DIR / "__init__.py",
        '"""Local agent-contracts scaffold."""\n',
        force=force,
        written=written,
    )
    _write(
        base / DEFAULT_SCAFFOLD_DIR / "adapter.py",
        render_python_adapter(DEFAULT_POLICY_FILENAME),
        force=force,
        written=written,
    )
    _write(
        base / DEFAULT_SCAFFOLD_DIR / "README.md",
        render_scaffold_readme(workspace_root),
        force=force,
        written=written,
    )
    return written
