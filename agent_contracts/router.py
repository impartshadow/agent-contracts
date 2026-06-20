"""Small tool-router adapter for putting contracts in front of tool calls."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Optional

from .contracts import default_contracts
from .core import ActionContext, CheckResult, Registry


Tool = Callable[..., Any]


class ContractedToolRouter:
    """Dispatch tools only after the registry's pre gate passes.

    This is intentionally tiny. Most agent frameworks already have a tool router;
    the useful part is the boundary shape: convert the intended call into an
    ``ActionContext``, run ``enforce_pre``, then execute the real tool.
    """

    def __init__(self, tools: dict[str, Tool], registry: Optional[Registry] = None):
        self.tools = dict(tools)
        self.registry = registry or Registry(default_contracts())
        self.edits_by_path: dict[str, int] = defaultdict(int)
        self.tool_calls: list[str] = []

    def call(self, tool: str, params: dict[str, Any]) -> Any:
        """Run one tool call after checking pre-action contracts."""

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

    def check_response(self, text: str) -> CheckResult:
        """Run post-action contracts over the final response text."""

        return self.registry.check_post(
            ActionContext(
                action="respond",
                response_text=text,
                tool_calls=list(self.tool_calls),
            )
        )
