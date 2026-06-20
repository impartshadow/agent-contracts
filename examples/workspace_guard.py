"""Demonstrate WorkspacePathGuard.

Run with:

    python examples/workspace_guard.py
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from agent_contracts import (
    ActionContext,
    BlockedAction,
    Registry,
    WorkspacePathGuard,
)


def main() -> int:
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()

        registry = Registry([WorkspacePathGuard(str(workspace))])

        allowed = ActionContext(
            action="tool_call",
            tool="write_file",
            params={"path": "notes.md"},
        )
        registry.enforce_pre(allowed)
        print("allowed: notes.md stays inside the workspace")

        blocked = ActionContext(
            action="tool_call",
            tool="write_file",
            params={"path": "../outside.txt"},
        )
        try:
            registry.enforce_pre(blocked)
        except BlockedAction as exc:
            print(f"blocked: {exc.violations[0].contract}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

