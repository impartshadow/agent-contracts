"""Dependency-free OpenAI tool-call adapter shape.

The real OpenAI SDK returns tool calls with a function name and JSON argument
string. This example uses the same shape without importing the SDK.

Run it:

    python examples/openai_tool_call_adapter.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from agent_contracts import ActionContext, BlockedAction, Registry, default_contracts


@dataclass
class FunctionCall:
    name: str
    arguments: str


@dataclass
class ToolCall:
    function: FunctionCall


def write_file(path: str, content: str) -> str:
    return f"wrote {len(content)} bytes to {path}"


TOOLS = {
    "write_file": write_file,
}


def dispatch_tool_call(tool_call: ToolCall, registry: Registry) -> str:
    name = tool_call.function.name
    params = json.loads(tool_call.function.arguments or "{}")

    ctx = ActionContext(action="tool_call", tool=name, params=params)
    registry.enforce_pre(ctx)

    return TOOLS[name](**params)


def main() -> None:
    registry = Registry(default_contracts())

    clean = ToolCall(FunctionCall("write_file", '{"path": "notes.md", "content": "ok\\n"}'))
    print(dispatch_tool_call(clean, registry))

    dangerous = ToolCall(
        FunctionCall("write_file", '{"path": "/etc/cron.d/backdoor", "content": "* * * * * root sh"}')
    )
    try:
        dispatch_tool_call(dangerous, registry)
    except BlockedAction as exc:
        print("blocked:", exc.violations[0].contract)


if __name__ == "__main__":
    main()
