from agent_contracts import (
    ActionContext,
    BlockedAction,
    Registry,
    Severity,
    ContractedToolRouter,
    default_contracts,
)
from agent_contracts.contracts import (
    DangerousPathGuard,
    LoopGuard,
    SecretLeakGuard,
    ShellCommandGuard,
    ToolAllowlistGuard,
    UnverifiedCompletionGuard,
    WorkspacePathGuard,
)
from agent_contracts.__main__ import main as cli_main

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


def test_workspace_path_guard_allows_relative_path_inside_root(tmp_path):
    g = WorkspacePathGuard(str(tmp_path))
    ctx = ActionContext(params={"path": "notes/today.md"})
    assert g.check_pre(ctx) is None


def test_workspace_path_guard_blocks_parent_traversal(tmp_path):
    g = WorkspacePathGuard(str(tmp_path / "project"))
    ctx = ActionContext(params={"path": "../outside.txt"})
    v = g.check_pre(ctx)
    assert v is not None and v.blocking


def test_workspace_path_guard_blocks_absolute_path_outside_root(tmp_path):
    root = tmp_path / "project"
    outside = tmp_path / "outside.txt"
    g = WorkspacePathGuard(str(root))
    ctx = ActionContext(params={"path": str(outside)})
    v = g.check_pre(ctx)
    assert v is not None and v.blocking


def test_workspace_path_guard_allows_absolute_path_inside_root(tmp_path):
    root = tmp_path / "project"
    inside = root / "notes.md"
    g = WorkspacePathGuard(str(root))
    ctx = ActionContext(params={"path": str(inside)})
    assert g.check_pre(ctx) is None


def test_shell_command_guard_blocks_sudo():
    g = ShellCommandGuard()
    ctx = ActionContext(action="tool_call", tool="run_shell", params={"cmd": "sudo systemctl restart app"})
    v = g.check_pre(ctx)
    assert v is not None and v.blocking


def test_shell_command_guard_blocks_root_recursive_delete():
    g = ShellCommandGuard()
    ctx = ActionContext(action="tool_call", tool="bash", params={"command": "rm -rf /"})
    v = g.check_pre(ctx)
    assert v is not None and v.blocking


def test_shell_command_guard_blocks_redirect_to_etc():
    g = ShellCommandGuard()
    ctx = ActionContext(action="tool_call", tool="exec_command", params={"cmd": "echo x > /etc/cron.d/x"})
    v = g.check_pre(ctx)
    assert v is not None and v.blocking


def test_shell_command_guard_allows_workspace_command():
    g = ShellCommandGuard()
    ctx = ActionContext(action="tool_call", tool="run_shell", params={"cmd": "pytest -q"})
    assert g.check_pre(ctx) is None


def test_shell_command_guard_ignores_non_shell_tool():
    g = ShellCommandGuard()
    ctx = ActionContext(action="tool_call", tool="write_file", params={"cmd": "sudo reboot"})
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


def test_violation_serializes_to_dict():
    violation = DangerousPathGuard().check_pre(ActionContext(params={"path": "/etc/passwd"}))
    assert violation is not None
    assert violation.to_dict() == {
        "contract": "dangerous-path-guard",
        "message": "write to protected path '/etc/passwd' (matched '/etc/')",
        "severity": "block",
        "blocking": True,
        "recovery": "Write to the project workspace, not a system path.",
    }


def test_check_result_serializes_to_dict():
    reg = Registry(default_contracts())
    result = reg.check_pre(ActionContext(action="tool_call", params={"path": "/etc/passwd"}))
    payload = result.to_dict()
    assert payload["passed"] is False
    assert payload["blocked"] is True
    assert payload["violations"][0]["contract"] == "dangerous-path-guard"


def test_contracted_tool_router_runs_allowed_call():
    router = ContractedToolRouter({"echo": lambda value: value})
    assert router.call("echo", {"value": "ok"}) == "ok"
    assert router.tool_calls == ["echo"]


def test_contracted_tool_router_blocks_before_dispatch():
    called = False

    def write_file(path, content):
        nonlocal called
        called = True
        return "wrote"

    router = ContractedToolRouter({"write_file": write_file})
    with pytest.raises(BlockedAction):
        router.call("write_file", {"path": "/etc/passwd", "content": "x"})
    assert called is False


def test_contracted_tool_router_tracks_edits_by_path():
    router = ContractedToolRouter({"write_file": lambda path, content: "wrote"})
    router.call("write_file", {"path": "notes.md", "content": "one"})
    router.call("write_file", {"path": "notes.md", "content": "two"})
    router.call("write_file", {"path": "notes.md", "content": "three"})

    with pytest.raises(BlockedAction):
        router.call("write_file", {"path": "notes.md", "content": "four"})


def test_contracted_tool_router_rejects_unknown_tool_after_contracts_pass():
    router = ContractedToolRouter({})
    with pytest.raises(ValueError, match="unknown tool"):
        router.call("missing", {})


def test_contracted_tool_router_checks_response_text():
    router = ContractedToolRouter({})
    result = router.check_response("Done, fixed it.")
    assert {v.contract for v in result.violations} == {"unverified-completion-guard"}


def test_module_cli_demo(capsys):
    assert cli_main() == 0
    output = capsys.readouterr().out
    assert "agent-contracts demo" in output
    assert "clean:" in output
    assert "blocked: dangerous-path-guard" in output
    assert "warn: unverified-completion-guard" in output
