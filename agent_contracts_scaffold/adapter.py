"""Local agent-contracts adapter.

Import these helpers at the shared tool dispatcher boundary. The important rule:
call ``gate_tool_call`` before the side-effecting tool runs, and call
``gate_response`` before text leaves the agent.
"""

from __future__ import annotations

from typing import Optional

from agent_contracts import ActionContext, load_policy


REGISTRY = load_policy("agent-contracts.yml")


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
            edits_by_path=edits_by_path or {},
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
