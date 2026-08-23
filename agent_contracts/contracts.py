"""A starter set of generic contracts.

These are intentionally simple and dependency-free. They are meant to be read,
copied, and adapted — not treated as a complete security boundary. Each one
encodes a failure mode that shows up across almost every autonomous agent:
runaway loops, writes to dangerous paths, leaked secrets, and fabricated
completion claims.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Iterable, Optional

from .core import ActionContext, Contract, Severity, Violation


class ToolAllowlistGuard(Contract):
    """Block tool calls outside an explicit allowlist.

    Use this when one agent role should only be able to reach a narrow tool set:
    a research agent can read and browse, a publisher can publish, a database
    migrator can run migrations but not send email. This is deliberately
    configurable and is not included in ``default_contracts`` because every
    runtime has a different tool surface.
    """

    name = "tool-allowlist-guard"

    def __init__(self, allowed_tools: Iterable[str]):
        self.allowed_tools = set(allowed_tools)

    def check_pre(self, ctx: ActionContext) -> Optional[Violation]:
        if ctx.action != "tool_call" or not ctx.tool:
            return None
        if ctx.tool not in self.allowed_tools:
            allowed = ", ".join(sorted(self.allowed_tools)) or "(none)"
            return self._violation(
                f"tool {ctx.tool!r} is not in the allowed tool set: {allowed}",
                recovery="Route this request to an agent role with the right tool authority.",
            )
        return None


class LoopGuard(Contract):
    """Stop an agent that keeps rewriting the same file.

    A classic runaway pattern: the model edits a file, doesn't like the result,
    edits it again, and again. After ``max_edits`` edits to one path in a turn,
    block — something is stuck and a human (or a different strategy) should look.
    """

    name = "loop-guard"

    def __init__(self, max_edits: int = 3):
        self.max_edits = max_edits

    def check_pre(self, ctx: ActionContext) -> Optional[Violation]:
        path = ctx.params.get("path") or ctx.params.get("file")
        if not path:
            return None
        count = ctx.edits_by_path.get(path, 0)
        if count >= self.max_edits:
            return self._violation(
                f"{count} edits to {path!r} this turn (limit {self.max_edits}) — "
                f"likely a stuck loop",
                recovery="Re-read the file and the goal before editing again, or escalate.",
            )
        return None


class DangerousPathGuard(Contract):
    """Block writes to system and home-config paths."""

    name = "dangerous-path-guard"

    _DEFAULT_BLOCKED = (
        "/etc/", "/usr/", "/bin/", "/sbin/", "/boot/", "/sys/", "/proc/",
        "/var/lib/", "/.ssh/", "/.aws/", "/.config/",
    )

    def __init__(self, blocked_prefixes: Optional[tuple[str, ...]] = None):
        self.blocked_prefixes = blocked_prefixes or self._DEFAULT_BLOCKED

    def check_pre(self, ctx: ActionContext) -> Optional[Violation]:
        path = ctx.params.get("path") or ctx.params.get("file")
        if not path:
            return None
        normalized = str(path)
        for prefix in self.blocked_prefixes:
            if prefix in normalized:
                return self._violation(
                    f"write to protected path {normalized!r} (matched {prefix!r})",
                    recovery="Write to the project workspace, not a system path.",
                )
        return None


class WorkspacePathGuard(Contract):
    """Block file actions that escape an allowed workspace root.

    Use this when an agent should be able to write inside a project directory but
    not elsewhere on the host. Unlike ``DangerousPathGuard``, this is not a list
    of forbidden prefixes; it is a positive boundary around one directory.
    """

    name = "workspace-path-guard"

    def __init__(
        self,
        workspace_root: str,
        path_keys: Optional[Iterable[str]] = None,
    ):
        self.workspace_root = Path(workspace_root).expanduser().resolve(strict=False)
        self.path_keys = tuple(path_keys or ("path", "file", "filename"))

    def check_pre(self, ctx: ActionContext) -> Optional[Violation]:
        for key in self.path_keys:
            raw_path = ctx.params.get(key)
            if not raw_path:
                continue
            candidate = Path(str(raw_path)).expanduser()
            if not candidate.is_absolute():
                candidate = self.workspace_root / candidate
            resolved = candidate.resolve(strict=False)
            try:
                resolved.relative_to(self.workspace_root)
            except ValueError:
                return self._violation(
                    f"path {str(raw_path)!r} resolves outside workspace {str(self.workspace_root)!r}",
                    recovery="Write inside the configured workspace root or route through an approval path.",
                )
        return None


class ShellCommandGuard(Contract):
    """Block common high-blast-radius shell commands.

    This is a starter guard for agent runtimes that expose shell execution as a
    tool. It is intentionally conservative and deterministic. It is not a shell
    sandbox; it catches the obvious commands that should not be agent-runnable
    without a narrower, runtime-specific approval path.
    """

    name = "shell-command-guard"

    _SHELL_TOOLS = {"shell", "bash", "run_shell", "exec", "exec_command"}
    _BLOCKED_PATTERNS = (
        (re.compile(r"\bsudo\b"), "sudo is outside the default agent shell boundary"),
        (re.compile(r"\brm\s+-[^;&|]*r[^;&|]*f?\s+/(?:\s|$)"), "recursive delete against /"),
        (re.compile(r"\brm\s+-[^;&|]*f[^;&|]*r\s+/(?:\s|$)"), "recursive delete against /"),
        (re.compile(r"\bmkfs(?:\.[\w.-]+)?\b"), "filesystem formatting command"),
        (re.compile(r"\bdd\s+.*\bof=/dev/"), "raw disk write with dd"),
        (re.compile(r"\bchmod\s+-R\s+777\b"), "recursive world-writable chmod"),
        (re.compile(r"\b(?:curl|wget)\b[^;&|]*(?:\||\s+-O\s+).*?\b(?:sh|bash)\b"), "download-to-shell execution"),
        (re.compile(r">\s*/(?:etc|usr|bin|sbin|boot|var/lib)/"), "redirect into protected system path"),
    )

    def __init__(self, shell_tools: Optional[Iterable[str]] = None):
        self.shell_tools = set(shell_tools or self._SHELL_TOOLS)

    def check_pre(self, ctx: ActionContext) -> Optional[Violation]:
        if ctx.action != "tool_call" or ctx.tool not in self.shell_tools:
            return None
        command = (
            ctx.params.get("cmd")
            or ctx.params.get("command")
            or ctx.params.get("script")
            or ""
        )
        if not command:
            return None
        text = str(command)
        for pattern, reason in self._BLOCKED_PATTERNS:
            if pattern.search(text):
                return self._violation(
                    f"blocked shell command: {reason}",
                    recovery="Use a narrower tool, a workspace-scoped command, or an explicit approval path.",
                )
        return None


class SecretLeakGuard(Contract):
    """Catch secrets in outgoing text or tool parameters before they leave.

    Matches common high-entropy credential shapes: private key blocks, AWS keys,
    GitHub/Slack/Stripe tokens, and ``KEY=...`` style env assignments. This is a
    last-line backstop, not a substitute for keeping secrets out of context.
    """

    name = "secret-leak-guard"

    _PATTERNS = (
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
        r"\bAKIA[0-9A-Z]{16}\b",                       # AWS access key id
        r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",             # GitHub tokens
        r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",           # Slack tokens
        r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b",  # Stripe secret keys
        r"\b[A-Z][A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|API_?KEY)\s*=\s*\S{8,}",
    )

    def __init__(self):
        self._compiled = [re.compile(p) for p in self._PATTERNS]

    def _scan(self, text: str) -> Optional[str]:
        for rx in self._compiled:
            m = rx.search(text)
            if m:
                return rx.pattern
        return None

    def check_pre(self, ctx: ActionContext) -> Optional[Violation]:
        blob = " ".join(str(v) for v in ctx.params.values())
        hit = self._scan(blob)
        if hit:
            return self._violation(
                f"possible secret in tool params (pattern {hit!r})",
                recovery="Redact the credential or pass a reference, not the raw value.",
            )
        return None

    def check_post(self, ctx: ActionContext) -> Optional[Violation]:
        hit = self._scan(ctx.response_text)
        if hit:
            return self._violation(
                f"possible secret in response text (pattern {hit!r})",
                recovery="Remove the credential from the reply.",
            )
        return None


class UnverifiedCompletionGuard(Contract):
    """Warn when the agent claims completion without showing evidence.

    "Done", "shipped", "fixed" are cheap to say and expensive to trust. If the
    response asserts completion but carries no verifiable artifact (a command
    output block, a URL, a hash, a file path), flag it. This is a *warn* by
    default — it nudges rather than blocks.
    """

    name = "unverified-completion-guard"

    _CLAIM = re.compile(
        r"\b(?:done|shipped|fixed|complete[d]?|deployed|merged|all set)\b",
        re.IGNORECASE,
    )
    _EVIDENCE = re.compile(
        r"```|https?://|\b[0-9a-f]{7,40}\b|(?:/[\w.-]+){2,}",  # code block, url, hash, path
    )

    def check_post(self, ctx: ActionContext) -> Optional[Violation]:
        if ctx.action != "respond":
            return None
        text = ctx.response_text
        if self._CLAIM.search(text) and not self._EVIDENCE.search(text):
            return self._violation(
                "completion claim with no verifiable artifact (no output, url, hash, or path)",
                severity=Severity.WARN,
                recovery="Paste the command output, link, commit hash, or file path that proves it.",
            )
        return None


class IdempotencyGuard(Contract):
    """Block re-execution of a side-effectful tool call that already ran.

    The classic production failure: a task retries (timeout, worker re-dispatch,
    max_retry_limit) and the payment/email/webhook fires twice. The framework
    can't see the gap between "tool executed" and "agent got the result" — so
    the guard has to live outside the agent loop, keyed on the call itself.

    How it works:

    1. Before execution, compute a deterministic idempotency key:
       ``sha256(tool_name, canonical_params, scope_id)``. The scope id
       (task/run id, from ``ctx.metadata``) is part of the key so legitimate
       repeat calls across *different* tasks are not blocked.
    2. Consult an append-only JSONL ledger for that key. Hit -> block, and
       surface the recorded result so the caller can replay it instead of
       re-executing. Miss -> allow.
    3. Call :meth:`reserve` *before* the external call and :meth:`record`
       after it returns. Recording alone leaves a window open between the
       side effect succeeding and the ledger append — a crash there loses all
       evidence and the retry re-fires the payment.

    A ``pending`` hit is not a ``terminal`` hit. It means a prior attempt
    reached the external system and the outcome is unknown, so there is no
    result to replay. Both block, but only a terminal hit can be replayed;
    a pending hit has to be reconciled against the provider, or explicitly
    resolved with :meth:`resolve_pending`.

    Only tools listed in ``guarded_tools`` are keyed; read-only tools should
    not pay the ledger cost and repeat reads are legitimate. Not included in
    ``default_contracts`` because the guarded tool set and ledger location are
    runtime-specific.
    """

    name = "idempotency-guard"

    def __init__(
        self,
        ledger_path: str,
        guarded_tools: Iterable[str],
        scope_key: str = "task_id",
    ):
        self.ledger_path = Path(ledger_path).expanduser()
        self.guarded_tools = set(guarded_tools)
        self.scope_key = scope_key

    def key_for(self, ctx: ActionContext) -> str:
        payload = json.dumps(
            [ctx.tool, ctx.params, ctx.metadata.get(self.scope_key, "")],
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def lookup(self, key: str) -> Optional[dict]:
        """Return the latest ledger record for ``key``, or None.

        The ledger is append-only, so a reserved-then-recorded call has two
        entries; the last one wins.
        """
        if not self.ledger_path.exists():
            return None
        found = None
        for line in self.ledger_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("key") == key:
                found = rec
        return found

    def _append(self, key: str, ctx: ActionContext, state: str, result: object) -> str:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "key": key,
            "tool": ctx.tool,
            "ts": time.time(),
            "state": state,
            "result": result,
        }
        with self.ledger_path.open("a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return key

    def reserve(self, ctx: ActionContext) -> str:
        """Append a ``pending`` record *before* the external call.

        This is what closes the crash window: if the process dies after the
        provider commits but before :meth:`record` runs, the pending entry is
        the only evidence the call ever happened.
        """
        return self._append(self.key_for(ctx), ctx, "pending", None)

    def record(self, ctx: ActionContext, result: object = None) -> str:
        """Append the terminal record once the side effect has returned."""
        return self._append(self.key_for(ctx), ctx, "terminal", result)

    def resolve_pending(self, ctx: ActionContext, result: object = None) -> str:
        """Close out a pending record after reconciling with the provider.

        Use when a prior attempt left a pending entry and you have since
        established what actually happened upstream. ``result=None`` means the
        side effect did not land and the call may be re-attempted.
        """
        if result is None:
            return self._append(self.key_for(ctx), ctx, "unresolved", None)
        return self._append(self.key_for(ctx), ctx, "terminal", result)

    def check_pre(self, ctx: ActionContext) -> Optional[Violation]:
        if ctx.action != "tool_call" or ctx.tool not in self.guarded_tools:
            return None
        rec = self.lookup(self.key_for(ctx))
        if rec is None:
            return None
        state = rec.get("state", "terminal")
        if state == "unresolved":
            return None
        if state == "pending":
            return self._violation(
                f"in-flight execution of side-effectful tool {ctx.tool!r} — "
                f"a prior attempt reached the external system at "
                f"ts={rec.get('ts')} and its outcome was never recorded",
                recovery=(
                    "Do not re-execute and do not replay: there is no recorded "
                    "result. Reconcile against the provider (query the charge, "
                    "message, or order by its own id), then call "
                    "resolve_pending() with the real outcome."
                ),
            )
        return self._violation(
            f"duplicate execution of side-effectful tool {ctx.tool!r} — "
            f"identical call already recorded at ts={rec.get('ts')}",
            recovery=(
                "Replay the recorded result instead of re-executing: "
                f"{json.dumps(rec.get('result'), default=str)[:200]}"
            ),
        )


def default_contracts() -> list[Contract]:
    """A sensible starter pack."""
    return [
        LoopGuard(),
        DangerousPathGuard(),
        ShellCommandGuard(),
        SecretLeakGuard(),
        UnverifiedCompletionGuard(),
    ]
