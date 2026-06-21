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
    ShellCommandGuard,
    ToolAllowlistGuard,
    UnverifiedCompletionGuard,
    WorkspacePathGuard,
    default_contracts,
)
from .router import ContractedToolRouter
from .policy import (
    DEFAULT_POLICY_FILENAME,
    load_policy,
    parse_policy,
    registry_from_policy,
    render_policy,
    write_policy,
)
from .matrix import MatrixScenario, contract_matrix, run_contract_matrix
from .replay import context_from_record, load_jsonl, replay_file, replay_records
from .eval import evaluate_records
from .doctor import run_doctor
from .sarif import replay_rows_to_sarif
from .scaffold import (
    DEFAULT_SCAFFOLD_DIR,
    DEFAULT_WORKFLOW_PATH,
    render_github_actions,
    render_python_adapter,
    render_scaffold_readme,
    write_scaffold,
)

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
    "ShellCommandGuard",
    "ToolAllowlistGuard",
    "UnverifiedCompletionGuard",
    "WorkspacePathGuard",
    "ContractedToolRouter",
    "DEFAULT_POLICY_FILENAME",
    "load_policy",
    "parse_policy",
    "registry_from_policy",
    "render_policy",
    "write_policy",
    "default_contracts",
    "MatrixScenario",
    "contract_matrix",
    "run_contract_matrix",
    "context_from_record",
    "load_jsonl",
    "replay_file",
    "replay_records",
    "evaluate_records",
    "run_doctor",
    "replay_rows_to_sarif",
    "DEFAULT_SCAFFOLD_DIR",
    "DEFAULT_WORKFLOW_PATH",
    "render_github_actions",
    "render_python_adapter",
    "render_scaffold_readme",
    "write_scaffold",
]
