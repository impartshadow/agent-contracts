"""MCP-style tool adapter example.

This example intentionally avoids importing an MCP SDK. The point is the adapter
shape: every authenticated tool call is converted into an ActionContext before
the local/server-side implementation runs.
"""

from __future__ import annotations

from agent_contracts import ActionContext, BlockedAction, Registry, default_contracts


registry = Registry(default_contracts())


def write_file(path: str, content: str) -> dict[str, object]:
    return {"ok": True, "bytes": len(content), "path": path}


TOOLS = {
    "write_file": write_file,
}


def dispatch_mcp_tool_call(name: str, arguments: dict[str, object]) -> dict[str, object]:
    """Gate an MCP tool call before dispatching to the implementation."""

    ctx = ActionContext(action="tool_call", tool=name, params=arguments)
    registry.enforce_pre(ctx)
    if name not in TOOLS:
        raise ValueError(f"unknown MCP tool: {name}")
    return TOOLS[name](**arguments)


if __name__ == "__main__":
    print(dispatch_mcp_tool_call("write_file", {"path": "notes.md", "content": "ok"}))
    try:
        dispatch_mcp_tool_call("write_file", {"path": "/etc/passwd", "content": "no"})
    except BlockedAction as exc:
        print(exc.violations[0].to_dict())
