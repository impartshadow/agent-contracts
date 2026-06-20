from agent_contracts import (
    ActionContext,
    BlockedAction,
    Registry,
    Severity,
    default_contracts,
)
from agent_contracts.contracts import (
    DangerousPathGuard,
    LoopGuard,
    SecretLeakGuard,
    ToolAllowlistGuard,
    UnverifiedCompletionGuard,
)

import pytest


def test_loop_guard_blocks_after_limit():
    g = LoopGuard(max_edits=3)
    ctx = ActionContext(
        action="tool_call",
        params={"path": "a.py"},
        edits_by_path={"a.py": 3},
    )
    v = g.check_pre(ctx)
    assert v is not None and v.blocking


def test_loop_guard_passes_under_limit():
    g = LoopGuard(max_edits=3)
    ctx = ActionContext(params={"path": "a.py"}, edits_by_path={"a.py": 1})
    assert g.check_pre(ctx) is None


def test_dangerous_path_blocks_etc():
    g = DangerousPathGuard()
    ctx = ActionContext(params={"path": "/etc/passwd"})
    v = g.check_pre(ctx)
    assert v is not None and v.blocking


def test_dangerous_path_allows_workspace():
    g = DangerousPathGuard()
    ctx = ActionContext(params={"path": "/home/me/project/main.py"})
    assert g.check_pre(ctx) is None


def test_tool_allowlist_blocks_unknown_tool():
    g = ToolAllowlistGuard({"read_file", "write_file"})
    ctx = ActionContext(action="tool_call", tool="send_email")
    v = g.check_pre(ctx)
    assert v is not None and v.blocking


def test_tool_allowlist_allows_known_tool():
    g = ToolAllowlistGuard({"read_file", "write_file"})
    ctx = ActionContext(action="tool_call", tool="write_file")
    assert g.check_pre(ctx) is None


def test_secret_leak_in_params():
    g = SecretLeakGuard()
    ctx = ActionContext(params={"body": "token AKIAIOSFODNN7EXAMPLE here"})
    assert g.check_pre(ctx) is not None


def test_secret_leak_in_response():
    g = SecretLeakGuard()
    key = "-----BEGIN PRIVATE KEY-----"
    ctx = ActionContext(action="respond", response_text=f"here you go: {key}")
    assert g.check_post(ctx) is not None


def test_secret_leak_clean_text():
    g = SecretLeakGuard()
    ctx = ActionContext(action="respond", response_text="no secrets in this sentence")
    assert g.check_post(ctx) is None


def test_unverified_completion_warns():
    g = UnverifiedCompletionGuard()
    ctx = ActionContext(action="respond", response_text="All done, fixed it.")
    v = g.check_post(ctx)
    assert v is not None and v.severity == Severity.WARN


def test_completion_with_evidence_passes():
    g = UnverifiedCompletionGuard()
    ctx = ActionContext(
        action="respond",
        response_text="Done. Pushed as a1b2c3d4 to main.",
    )
    assert g.check_post(ctx) is None


def test_registry_collects_all_violations():
    reg = Registry(default_contracts())
    ctx = ActionContext(
        action="tool_call",
        params={"path": "/etc/cron.d/x", "body": "AKIAIOSFODNN7EXAMPLE"},
        edits_by_path={"/etc/cron.d/x": 5},
    )
    result = reg.check_pre(ctx)
    fired = {v.contract for v in result.violations}
    assert {"dangerous-path-guard", "secret-leak-guard", "loop-guard"} <= fired
    assert result.blocked


def test_enforce_pre_raises_on_block():
    reg = Registry(default_contracts())
    ctx = ActionContext(action="tool_call", params={"path": "/etc/passwd"})
    with pytest.raises(BlockedAction):
        reg.enforce_pre(ctx)


def test_clean_action_passes():
    reg = Registry(default_contracts())
    ctx = ActionContext(action="tool_call", params={"path": "notes.md", "content": "hi"})
    result = reg.check_pre(ctx)
    assert result.passed and bool(result) is True
