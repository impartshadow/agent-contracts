"""agent-contracts: deterministic pre/post-condition guardrails for LLM agents.

Quickstart::

    from agent_contracts import Registry, ActionContext, default_contracts

    registry = Registry(default_contracts())

    ctx = ActionContext(action="tool_call", tool="write_file",
                        params={"path": "/etc/passwd", "content": "..."})
    result = registry.check_pre(ctx)
    if result.blocked:
        for v in result.violations:
            print(v.contract, "->", v.message)
"""

from .core import (
    ActionContext,
    BlockedAction,
    CheckResult,
    Contract,
    Registry,
    Severity,
    Violation,
)
from .contracts import (
    DangerousPathGuard,
    LoopGuard,
    SecretLeakGuard,
    ToolAllowlistGuard,
    UnverifiedCompletionGuard,
    default_contracts,
)
from .router import ContractedToolRouter

__version__ = "0.1.0"

__all__ = [
    "ActionContext",
    "BlockedAction",
    "CheckResult",
    "Contract",
    "Registry",
    "Severity",
    "Violation",
    "DangerousPathGuard",
    "LoopGuard",
    "SecretLeakGuard",
    "ToolAllowlistGuard",
    "UnverifiedCompletionGuard",
    "ContractedToolRouter",
    "default_contracts",
]
