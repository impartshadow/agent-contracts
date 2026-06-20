"""Executable examples for every built-in contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .contracts import (
    DangerousPathGuard,
    LoopGuard,
    SecretLeakGuard,
    ShellCommandGuard,
    ToolAllowlistGuard,
    UnverifiedCompletionGuard,
    WorkspacePathGuard,
)
from .core import ActionContext, CheckResult, Registry


@dataclass(frozen=True)
class MatrixScenario:
    """One canonical contract firing case."""

    name: str
    phase: str
    contract: str
    registry_factory: Callable[[], Registry]
    context_factory: Callable[[], ActionContext]
    expect_blocked: bool

    def run(self) -> CheckResult:
        registry = self.registry_factory()
        context = self.context_factory()
        if self.phase == "pre":
            return registry.check_pre(context)
        if self.phase == "post":
            return registry.check_post(context)
        raise ValueError(f"unknown matrix phase: {self.phase!r}")


def _registry(*contracts) -> Registry:
    return Registry(list(contracts))


def contract_matrix() -> list[MatrixScenario]:
    """Return canonical examples for the built-in contract set."""

    return [
        MatrixScenario(
            name="repeated-file-edit",
            phase="pre",
            contract="loop-guard",
            registry_factory=lambda: _registry(LoopGuard(max_edits=3)),
            context_factory=lambda: ActionContext(
                action="tool_call",
                tool="write_file",
                params={"path": "agent.py", "content": "..."},
                edits_by_path={"agent.py": 3},
            ),
            expect_blocked=True,
        ),
        MatrixScenario(
            name="system-path-write",
            phase="pre",
            contract="dangerous-path-guard",
            registry_factory=lambda: _registry(DangerousPathGuard()),
            context_factory=lambda: ActionContext(
                action="tool_call",
                tool="write_file",
                params={"path": "/etc/passwd", "content": "..."},
            ),
            expect_blocked=True,
        ),
        MatrixScenario(
            name="workspace-escape",
            phase="pre",
            contract="workspace-path-guard",
            registry_factory=lambda: _registry(WorkspacePathGuard("/srv/agent/workspace")),
            context_factory=lambda: ActionContext(
                action="tool_call",
                tool="write_file",
                params={"path": "../secrets.txt", "content": "..."},
            ),
            expect_blocked=True,
        ),
        MatrixScenario(
            name="root-shell-command",
            phase="pre",
            contract="shell-command-guard",
            registry_factory=lambda: _registry(ShellCommandGuard()),
            context_factory=lambda: ActionContext(
                action="tool_call",
                tool="run_shell",
                params={"cmd": "sudo systemctl restart prod"},
            ),
            expect_blocked=True,
        ),
        MatrixScenario(
            name="raw-secret-in-params",
            phase="pre",
            contract="secret-leak-guard",
            registry_factory=lambda: _registry(SecretLeakGuard()),
            context_factory=lambda: ActionContext(
                action="tool_call",
                tool="send_email",
                params={"body": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"},
            ),
            expect_blocked=True,
        ),
        MatrixScenario(
            name="unknown-tool-for-role",
            phase="pre",
            contract="tool-allowlist-guard",
            registry_factory=lambda: _registry(ToolAllowlistGuard({"read_file", "write_file"})),
            context_factory=lambda: ActionContext(
                action="tool_call",
                tool="send_email",
                params={"to": "customer@example.com"},
            ),
            expect_blocked=True,
        ),
        MatrixScenario(
            name="completion-claim-without-evidence",
            phase="post",
            contract="unverified-completion-guard",
            registry_factory=lambda: _registry(UnverifiedCompletionGuard()),
            context_factory=lambda: ActionContext(
                action="respond",
                response_text="Done. Fixed it.",
            ),
            expect_blocked=False,
        ),
    ]


def run_contract_matrix() -> list[dict[str, object]]:
    """Run the matrix and return stable JSON-serializable rows."""

    rows: list[dict[str, object]] = []
    for scenario in contract_matrix():
        result = scenario.run()
        fired = [violation.contract for violation in result.violations]
        expected_contract_fired = scenario.contract in fired
        expected_block_state = result.blocked is scenario.expect_blocked
        rows.append(
            {
                "name": scenario.name,
                "phase": scenario.phase,
                "expected_contract": scenario.contract,
                "expected_blocked": scenario.expect_blocked,
                "blocked": result.blocked,
                "fired_contracts": fired,
                "passed": expected_contract_fired and expected_block_state,
            }
        )
    return rows
