"""Load a generated policy file and enforce it at the tool boundary.

Run it:

    python examples/policy_loader.py
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from agent_contracts import BlockedAction, ContractedToolRouter, load_policy, write_policy


def write_file(path: str, content: str) -> str:
    return f"wrote {len(content)} bytes to {path}"


def main() -> None:
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        policy_path = Path(tmp) / "agent-contracts.yml"
        write_policy(policy_path, workspace_root=str(workspace))

        router = ContractedToolRouter({"write_file": write_file}, registry=load_policy(policy_path))
        print(router.call("write_file", {"path": "notes.md", "content": "ok\n"}))

        try:
            router.call("send_email", {"to": "person@example.com", "body": "surprise"})
        except BlockedAction as exc:
            print("blocked:", exc.violations[0].contract)


if __name__ == "__main__":
    main()
