"""Copy-paste pattern: put contracts at the tool router boundary.

This is the smallest useful integration shape for an agent runtime:

1. Convert the model's intended tool call into an ActionContext.
2. Run registry.enforce_pre(ctx) before dispatch.
3. Execute the real tool only if the gate passes.
4. Run registry.check_post(...) before returning final text to the user.

Run it:

    python examples/tool_router.py
"""

from __future__ import annotations

from agent_contracts import BlockedAction, ContractedToolRouter


def write_file(path: str, content: str) -> str:
    return f"wrote {len(content)} bytes to {path}"


def main() -> None:
    router = ContractedToolRouter({"write_file": write_file})

    print(router.call("write_file", {"path": "notes.md", "content": "ship it\n"}))

    try:
        router.call("write_file", {"path": "/etc/cron.d/backdoor", "content": "* * * * * root sh"})
    except BlockedAction as exc:
        print("blocked:", exc.violations[0].contract)

    result = router.check_response("Done. Pushed as f99d4ec to main.")
    print("response allowed:", not result.blocked)


if __name__ == "__main__":
    main()
