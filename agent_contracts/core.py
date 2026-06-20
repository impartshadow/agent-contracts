"""Core primitives: ActionContext, Violation, Contract, and the Registry.

The model is deliberately small. An agent is about to take an action (call a
tool, emit a response). Before it acts you run the *pre* gate; after it produces
output you run the *post* gate. Each contract is a deterministic function of the
context. A contract may pass (return ``None``) or fail (return a ``Violation``).

There is no LLM in the loop here — that is the point. Guardrails that depend on
a model to police the model fail exactly when the model misbehaves. These checks
are plain Python and run the same way every time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    """How hard a violation bites."""

    WARN = "warn"   # surface it, let the action through
    BLOCK = "block"  # stop the action


@dataclass
class ActionContext:
    """Everything a contract is allowed to look at.

    Populate the fields relevant to the action you are gating. Unused fields keep
    their defaults — contracts must tolerate empty context.
    """

    action: str = ""                       # e.g. "tool_call", "respond", "git_push"
    tool: str = ""                         # tool name when action == "tool_call"
    params: dict = field(default_factory=dict)   # tool/action parameters
    response_text: str = ""                # the outgoing text when action == "respond"
    user_message: str = ""                 # the request that triggered this turn
    files_written: list[str] = field(default_factory=list)
    tool_calls: list[str] = field(default_factory=list)  # tools called this turn
    edits_by_path: dict[str, int] = field(default_factory=dict)  # path -> edit count
    metadata: dict = field(default_factory=dict)  # escape hatch for app-specific state


@dataclass
class Violation:
    """A failed contract check."""

    contract: str
    message: str
    severity: Severity = Severity.BLOCK
    recovery: str = ""

    @property
    def blocking(self) -> bool:
        return self.severity == Severity.BLOCK


class Contract:
    """Base class for a guardrail.

    Override ``check_pre`` to gate an action before it runs, ``check_post`` to
    inspect output after it is produced, or both. Return a ``Violation`` to fire,
    or ``None`` to pass.
    """

    name: str = "base"

    def check_pre(self, ctx: ActionContext) -> Optional[Violation]:
        return None

    def check_post(self, ctx: ActionContext) -> Optional[Violation]:
        return None

    # convenience for subclasses
    def _violation(
        self,
        message: str,
        severity: Severity = Severity.BLOCK,
        recovery: str = "",
    ) -> Violation:
        return Violation(
            contract=self.name,
            message=message,
            severity=severity,
            recovery=recovery,
        )


@dataclass
class CheckResult:
    """The outcome of running a phase of the registry."""

    violations: list[Violation] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(v.blocking for v in self.violations)

    @property
    def passed(self) -> bool:
        return not self.violations

    def __bool__(self) -> bool:  # truthy == clean pass
        return self.passed


class BlockedAction(Exception):
    """Raised by :meth:`Registry.enforce_pre` when a blocking contract fires."""

    def __init__(self, violations: list[Violation]):
        self.violations = violations
        joined = "; ".join(f"[{v.contract}] {v.message}" for v in violations)
        super().__init__(f"action blocked by contract(s): {joined}")


class Registry:
    """Holds contracts and runs them as pre/post gates."""

    def __init__(self, contracts: Optional[list[Contract]] = None):
        self._contracts: list[Contract] = list(contracts or [])

    def register(self, contract: Contract) -> "Registry":
        self._contracts.append(contract)
        return self

    @property
    def contracts(self) -> list[Contract]:
        return list(self._contracts)

    def check_pre(self, ctx: ActionContext) -> CheckResult:
        """Run every pre gate, collecting all violations (no short-circuit)."""
        result = CheckResult()
        for c in self._contracts:
            v = c.check_pre(ctx)
            if v is not None:
                result.violations.append(v)
        return result

    def check_post(self, ctx: ActionContext) -> CheckResult:
        """Run every post gate, collecting all violations."""
        result = CheckResult()
        for c in self._contracts:
            v = c.check_post(ctx)
            if v is not None:
                result.violations.append(v)
        return result

    def enforce_pre(self, ctx: ActionContext) -> CheckResult:
        """Like :meth:`check_pre` but raises :class:`BlockedAction` if anything blocks.

        Use this to wrap a tool call: if it returns, the action is cleared to run.
        """
        result = self.check_pre(ctx)
        if result.blocked:
            raise BlockedAction([v for v in result.violations if v.blocking])
        return result
