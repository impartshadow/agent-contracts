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

from collections import defaultdict
from typing import Any, Callable

from agent_contracts import ActionContext, BlockedAction, Registry, default_contracts


Tool = Callable[..., str]


class ToolRouter:
    """A tiny tool dispatcher with deterministic pre/post gates."""

    def __init__(self, tools: dict[str, Tool], registry: Registry | None = None):
        self.tools = tools
        self.registry = registry or Registry(default_contracts())
        self.edits_by_path: dict[str, int] = defaultdict(int)
        self.tool_calls: list[str] = []

    def call(self, tool: str, params: dict[str, Any]) -> str:
        ctx = ActionContext(
            action="tool_call",
            tool=tool,
            params=params,
            tool_calls=list(self.tool_calls),
            edits_by_path=dict(self.edits_by_path),
        )
        self.registry.enforce_pre(ctx)

        if tool not in self.tools:
            raise ValueError(f"unknown tool: {tool}")

        result = self.tools[tool](**params)
        self.tool_calls.append(tool)

        path = params.get("path") or params.get("file")
        if path:
            self.edits_by_path[str(path)] += 1

        return result

    def final_response(self, text: str) -> str:
        result = self.registry.check_post(
            ActionContext(action="respond", response_text=text, tool_calls=list(self.tool_calls))
        )
        if result.blocked:
            names = ", ".join(v.contract for v in result.violations if v.blocking)
            return f"I need to redact or regenerate this response. Blocked by: {names}"
        return text


def write_file(path: str, content: str) -> str:
    return f"wrote {len(content)} bytes to {path}"


def main() -> None:
    router = ToolRouter({"write_file": write_file})

    print(router.call("write_file", {"path": "notes.md", "content": "ship it\n"}))

    try:
        router.call("write_file", {"path": "/etc/cron.d/backdoor", "content": "* * * * * root sh"})
    except BlockedAction as exc:
        print("blocked:", exc.violations[0].contract)

    print(router.final_response("Done. Pushed as f99d4ec to main."))


if __name__ == "__main__":
    main()
