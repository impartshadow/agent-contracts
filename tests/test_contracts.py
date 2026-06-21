from agent_contracts import (
    ActionContext,
    BlockedAction,
    Registry,
    Severity,
    ContractedToolRouter,
    default_contracts,
    load_policy,
    parse_policy,
    render_policy,
    replay_file,
    replay_records,
    replay_rows_to_sarif,
    evaluate_records,
    run_doctor,
    score_repository,
    render_scorecard_markdown,
    render_pre_commit_config,
    write_scaffold,
    run_contract_matrix,
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

import json
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


def test_score_repository_full_adoption(tmp_path):
    write_scaffold(str(tmp_path), workspace_root=str(tmp_path))
    eval_path = tmp_path / "eval.jsonl"
    eval_path.write_text(
        "\n".join(
            [
                '{"phase":"pre","tool":"write_file","params":{"path":"/etc/passwd"},"expected_blocked":true,"expected_contracts":["dangerous-path-guard"]}',
                '{"phase":"pre","tool":"write_file","params":{"path":"notes.md"},"expected_blocked":false}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    replay_path = tmp_path / "incidents.jsonl"
    replay_path.write_text(
        '{"phase":"pre","tool":"write_file","params":{"path":"/etc/passwd"}}\n',
        encoding="utf-8",
    )

    payload = score_repository(tmp_path, eval_path=eval_path, replay_path=replay_path)

    assert payload["score"] == 100
    assert payload["grade"] == "A"
    assert payload["passed"] is True
    assert "agent%20reliability-100%2F100" in payload["badge_url"]
    assert payload["badge_endpoint"]["message"] == "100/100"


def test_score_repository_missing_adoption_is_not_passing(tmp_path):
    payload = score_repository(tmp_path)

    assert payload["score"] == 30
    assert payload["grade"] == "F"
    assert payload["passed"] is False


def test_score_cli_badge(tmp_path, capsys):
    write_scaffold(str(tmp_path), workspace_root=str(tmp_path))

    code = cli_main(["score", "--root", str(tmp_path), "--badge"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.startswith("![Agent reliability: 60/100]")


def test_score_cli_writes_public_artifacts(tmp_path):
    write_scaffold(str(tmp_path), workspace_root=str(tmp_path))
    eval_path = tmp_path / "eval.jsonl"
    eval_path.write_text(
        '{"phase":"pre","tool":"write_file","params":{"path":"notes.md"},"expected_blocked":false}\n',
        encoding="utf-8",
    )
    score_json = tmp_path / "agent-reliability-score.json"
    score_md = tmp_path / "AGENT_RELIABILITY_SCORE.md"
    badge_json = tmp_path / "agent-reliability-badge.json"

    code = cli_main([
        "score",
        "--root",
        str(tmp_path),
        "--eval",
        str(eval_path),
        "--output-json",
        str(score_json),
        "--output-markdown",
        str(score_md),
        "--output-badge-json",
        str(badge_json),
    ])

    assert code == 0
    score_payload = json.loads(score_json.read_text())
    badge_payload = json.loads(badge_json.read_text())
    markdown = score_md.read_text()
    assert score_payload["score"] >= 70
    assert badge_payload["label"] == "agent reliability"
    assert "# Agent Reliability Score" in markdown


def test_render_scorecard_markdown_is_reproducible(tmp_path):
    write_scaffold(str(tmp_path), workspace_root=str(tmp_path))
    payload = score_repository(tmp_path)
    markdown = render_scorecard_markdown(payload)

    assert f"**Score: {payload['score']}/100" in markdown
    assert "| adoption_wiring |" in markdown


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
    assert cli_main([]) == 0
    output = capsys.readouterr().out
    assert "agent-contracts demo" in output
    assert "clean:" in output
    assert "blocked: dangerous-path-guard" in output
    assert "warn: unverified-completion-guard" in output


def test_cli_check_pre_blocks_with_json(capsys):
    exit_code = cli_main(
        [
            "check-pre",
            "--tool",
            "write_file",
            "--params-json",
            '{"path": "/etc/passwd", "content": "no"}',
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["blocked"] is True
    assert payload["violations"][0]["contract"] == "dangerous-path-guard"


def test_cli_check_pre_passes_clean_call(capsys):
    exit_code = cli_main(
        [
            "check-pre",
            "--tool",
            "write_file",
            "--params-json",
            '{"path": "notes.md", "content": "ok"}',
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert output.strip() == "pass"


def test_cli_check_post_warns_without_blocking(capsys):
    exit_code = cli_main(
        [
            "check-post",
            "--response-text",
            "Done, fixed it.",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "warn" in output
    assert "unverified-completion-guard" in output


def test_render_policy_includes_workspace_and_allowlist():
    policy = render_policy("/srv/agent")

    assert "root: /srv/agent" in policy
    assert "allowlist:" in policy
    assert "write_file" in policy
    assert "max_edits_per_path: 3" in policy


def test_cli_init_writes_policy_file(tmp_path, capsys):
    output = tmp_path / "contracts.yml"
    exit_code = cli_main(["init", "--output", str(output), "--workspace", "/tmp/project"])

    assert exit_code == 0
    assert "wrote" in capsys.readouterr().out
    text = output.read_text(encoding="utf-8")
    assert "root: /tmp/project" in text
    assert "completion_evidence:" in text


def test_cli_init_refuses_to_overwrite_without_force(tmp_path, capsys):
    output = tmp_path / "contracts.yml"
    output.write_text("keep me", encoding="utf-8")

    exit_code = cli_main(["init", "--output", str(output)])

    assert exit_code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "keep me"


def test_cli_init_force_overwrites_policy_file(tmp_path):
    output = tmp_path / "contracts.yml"
    output.write_text("replace me", encoding="utf-8")

    exit_code = cli_main(["init", "--output", str(output), "--workspace", ".", "--force"])

    assert exit_code == 0
    assert "agent-contracts starter policy" in output.read_text(encoding="utf-8")


def test_parse_policy_reads_generated_schema():
    policy = parse_policy(render_policy("/srv/agent"))

    assert policy["workspace"]["root"] == "/srv/agent"
    assert policy["workspace"]["path_keys"] == ["path", "file", "filename"]
    assert policy["tools"]["allowlist"] == [
        "read_file",
        "write_file",
        "list_files",
        "web_search",
        "run_tests",
    ]
    assert policy["loop_guard"]["max_edits_per_path"] == 3
    assert policy["secrets"]["block_in_tool_params"] is True


def test_load_policy_builds_registry_from_file(tmp_path):
    path = tmp_path / "agent-contracts.yml"
    path.write_text(render_policy(str(tmp_path / "project")), encoding="utf-8")

    registry = load_policy(path)
    outside = registry.check_pre(
        ActionContext(action="tool_call", tool="write_file", params={"path": "../outside.txt"})
    )
    unknown_tool = registry.check_pre(ActionContext(action="tool_call", tool="send_email"))

    assert outside.blocked
    assert "workspace-path-guard" in {v.contract for v in outside.violations}
    assert unknown_tool.blocked
    assert "tool-allowlist-guard" in {v.contract for v in unknown_tool.violations}


def test_cli_check_pre_accepts_policy_file(tmp_path, capsys):
    policy_path = tmp_path / "agent-contracts.yml"
    policy_path.write_text(render_policy(str(tmp_path / "project")), encoding="utf-8")

    exit_code = cli_main(
        [
            "check-pre",
            "--policy",
            str(policy_path),
            "--tool",
            "send_email",
            "--params-json",
            "{}",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["blocked"] is True
    assert "tool-allowlist-guard" in {v["contract"] for v in payload["violations"]}


def test_contract_matrix_covers_every_builtin_guard():
    rows = run_contract_matrix()

    assert all(row["passed"] for row in rows)
    assert {row["expected_contract"] for row in rows} == {
        "loop-guard",
        "dangerous-path-guard",
        "workspace-path-guard",
        "shell-command-guard",
        "secret-leak-guard",
        "tool-allowlist-guard",
        "unverified-completion-guard",
    }


def test_cli_matrix_outputs_canonical_examples(capsys):
    exit_code = cli_main(["matrix"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "agent-contracts matrix" in output
    assert "system-path-write" in output
    assert "completion-claim-without-evidence" in output


def test_cli_matrix_json(capsys):
    exit_code = cli_main(["matrix", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["passed"] is True
    assert any(row["expected_contract"] == "shell-command-guard" for row in payload["rows"])


def test_write_scaffold_creates_policy_adapter_workflow_and_readme(tmp_path):
    written = write_scaffold(tmp_path, workspace_root="/srv/agent")
    relative = {path.relative_to(tmp_path).as_posix() for path in written}

    assert relative == {
        "agent-contracts.yml",
        ".github/workflows/agent-contracts.yml",
        ".pre-commit-config.yaml",
        "agent_contracts_scaffold/__init__.py",
        "agent_contracts_scaffold/adapter.py",
        "agent_contracts_scaffold/README.md",
    }
    assert "root: /srv/agent" in (tmp_path / "agent-contracts.yml").read_text(encoding="utf-8")
    assert "gate_tool_call" in (tmp_path / "agent_contracts_scaffold/adapter.py").read_text(
        encoding="utf-8"
    )
    assert "agent-contracts matrix" in (
        tmp_path / ".github/workflows/agent-contracts.yml"
    ).read_text(encoding="utf-8")
    assert "agent-contracts doctor --root ." in (
        tmp_path / ".pre-commit-config.yaml"
    ).read_text(encoding="utf-8")


def test_write_scaffold_refuses_overwrite_without_force(tmp_path):
    (tmp_path / "agent-contracts.yml").write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_scaffold(tmp_path)

    assert (tmp_path / "agent-contracts.yml").read_text(encoding="utf-8") == "keep"


def test_cli_bootstrap_writes_repository_scaffold(tmp_path, capsys):
    exit_code = cli_main(["bootstrap", "--root", str(tmp_path), "--workspace", "/workspace"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "wrote" in output
    assert (tmp_path / "agent-contracts.yml").exists()
    assert (tmp_path / "agent_contracts_scaffold/adapter.py").exists()
    assert (tmp_path / ".github/workflows/agent-contracts.yml").exists()
    assert (tmp_path / ".pre-commit-config.yaml").exists()


def test_render_pre_commit_config_runs_matrix_and_doctor():
    text = render_pre_commit_config()

    assert "agent-contracts matrix" in text
    assert "agent-contracts doctor --root ." in text
    assert "pass_filenames: false" in text


def test_cli_bootstrap_reports_existing_file(tmp_path, capsys):
    (tmp_path / "agent-contracts.yml").write_text("keep", encoding="utf-8")

    exit_code = cli_main(["bootstrap", "--root", str(tmp_path)])

    assert exit_code == 1
    assert "already exists" in capsys.readouterr().err


def test_replay_records_runs_pre_and_post_checks():
    rows = replay_records(
        [
            {
                "phase": "pre",
                "action": "tool_call",
                "tool": "write_file",
                "params": {"path": "/etc/passwd"},
            },
            {"phase": "post", "action": "respond", "response_text": "Done, fixed it."},
        ],
        Registry(default_contracts()),
    )

    assert rows[0]["blocked"] is True
    assert rows[0]["violations"][0]["contract"] == "dangerous-path-guard"
    assert rows[1]["blocked"] is False
    assert rows[1]["violations"][0]["contract"] == "unverified-completion-guard"


def test_replay_file_reads_jsonl(tmp_path):
    path = tmp_path / "actions.jsonl"
    path.write_text(
        '{"phase":"pre","tool":"write_file","params":{"path":"notes.md"}}\n'
        '{"phase":"pre","tool":"write_file","params":{"path":"../outside.txt"}}\n',
        encoding="utf-8",
    )
    policy = tmp_path / "agent-contracts.yml"
    policy.write_text(render_policy(str(tmp_path / "project")), encoding="utf-8")

    rows = replay_file(path, load_policy(policy))

    assert rows[0]["blocked"] is False
    assert rows[1]["blocked"] is True
    assert rows[1]["line"] == 2


def test_cli_replay_reports_summary_and_blocks(tmp_path, capsys):
    path = tmp_path / "actions.jsonl"
    path.write_text(
        '{"phase":"pre","tool":"write_file","params":{"path":"/etc/passwd"}}\n',
        encoding="utf-8",
    )

    exit_code = cli_main(["replay", str(path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "replayed 1 records" in output
    assert "dangerous-path-guard" in output


def test_cli_replay_json(tmp_path, capsys):
    path = tmp_path / "actions.jsonl"
    path.write_text(
        '{"phase":"post","response_text":"Done, fixed it."}\n',
        encoding="utf-8",
    )

    exit_code = cli_main(["replay", str(path), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["blocked_count"] == 0
    assert payload["violation_count"] == 1
    assert payload["rows"][0]["violations"][0]["contract"] == "unverified-completion-guard"


def test_cli_replay_expect_blocks_passes_for_incident_fixture(tmp_path, capsys):
    path = tmp_path / "actions.jsonl"
    path.write_text(
        '{"phase":"pre","tool":"write_file","params":{"path":"/etc/passwd"}}\n',
        encoding="utf-8",
    )

    exit_code = cli_main(["replay", str(path), "--expect-blocks", "1"])

    assert exit_code == 0
    assert "1 blocked" in capsys.readouterr().out


def test_cli_replay_expect_blocks_fails_on_mismatch(tmp_path):
    path = tmp_path / "actions.jsonl"
    path.write_text(
        '{"phase":"pre","tool":"write_file","params":{"path":"/etc/passwd"}}\n',
        encoding="utf-8",
    )

    assert cli_main(["replay", str(path), "--expect-blocks", "0"]) == 1


def test_cli_replay_expect_violations_passes_with_warnings(tmp_path):
    path = tmp_path / "actions.jsonl"
    path.write_text(
        '{"phase":"post","response_text":"Done, fixed it."}\n',
        encoding="utf-8",
    )

    assert cli_main(["replay", str(path), "--expect-violations", "1"]) == 0


def test_cli_replay_json_passed_reflects_expectations(tmp_path, capsys):
    path = tmp_path / "actions.jsonl"
    path.write_text(
        '{"phase":"pre","tool":"write_file","params":{"path":"/etc/passwd"}}\n',
        encoding="utf-8",
    )

    exit_code = cli_main(["replay", str(path), "--expect-blocks", "1", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["passed"] is True
    assert payload["expectations"]["blocks"] == 1


def test_replay_rows_to_sarif_maps_violations_to_results():
    rows = replay_records(
        [
            {
                "phase": "pre",
                "action": "tool_call",
                "tool": "write_file",
                "params": {"path": "/etc/passwd"},
            }
        ],
        Registry(default_contracts()),
    )

    sarif = replay_rows_to_sarif(rows, "actions.jsonl")
    result = sarif["runs"][0]["results"][0]

    assert sarif["version"] == "2.1.0"
    assert result["ruleId"] == "dangerous-path-guard"
    assert result["level"] == "error"
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 1


def test_cli_replay_sarif(tmp_path, capsys):
    path = tmp_path / "actions.jsonl"
    path.write_text(
        '{"phase":"post","response_text":"Done, fixed it."}\n',
        encoding="utf-8",
    )

    exit_code = cli_main(["replay", str(path), "--sarif"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["runs"][0]["results"][0]["ruleId"] == "unverified-completion-guard"
    assert payload["runs"][0]["results"][0]["level"] == "warning"


def test_evaluate_records_reports_confusion_matrix():
    payload = evaluate_records(
        [
            {
                "phase": "pre",
                "tool": "write_file",
                "params": {"path": "/etc/passwd"},
                "expected_blocked": True,
                "expected_contracts": ["dangerous-path-guard"],
            },
            {
                "phase": "pre",
                "tool": "write_file",
                "params": {"path": "notes.md"},
                "expected_blocked": False,
            },
        ],
        Registry(default_contracts()),
    )

    assert payload["passed"] is True
    assert payload["true_positive"] == 1
    assert payload["true_negative"] == 1
    assert payload["false_positive"] == 0
    assert payload["false_negative"] == 0
    assert payload["precision"] == 1
    assert payload["recall"] == 1


def test_evaluate_records_detects_expected_contract_miss():
    payload = evaluate_records(
        [
            {
                "phase": "pre",
                "tool": "write_file",
                "params": {"path": "/etc/passwd"},
                "expected_blocked": True,
                "expected_contracts": ["shell-command-guard"],
            }
        ],
        Registry(default_contracts()),
    )

    assert payload["passed"] is False
    assert payload["contract_misses"][0]["missing_contracts"] == ["shell-command-guard"]


def test_cli_eval_reports_metrics(capsys):
    exit_code = cli_main(["eval", "examples/eval_corpus.jsonl"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "evaluated 7 records" in output
    assert "precision=1.00" in output
    assert "recall=1.00" in output


def test_cli_eval_json(capsys):
    exit_code = cli_main(["eval", "examples/eval_corpus.jsonl", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["passed"] is True
    assert payload["records"] == 7
    assert payload["true_positive"] == 3


def test_run_doctor_reports_bootstrap_readiness(tmp_path):
    write_scaffold(tmp_path, workspace_root=str(tmp_path))

    payload = run_doctor(tmp_path)

    assert payload["passed"] is True
    assert payload["required_passed"] == payload["required_total"]
    assert {check["name"] for check in payload["checks"]} >= {
        "policy",
        "adapter",
        "github-actions",
        "pre-commit",
        "built-in-matrix",
        "policy-load",
    }


def test_run_doctor_fails_missing_required_files(tmp_path):
    payload = run_doctor(tmp_path)

    assert payload["passed"] is False
    missing = {check["name"] for check in payload["checks"] if not check["passed"]}
    assert {"policy", "adapter", "github-actions"} <= missing


def test_cli_doctor_reports_status(tmp_path, capsys):
    write_scaffold(tmp_path, workspace_root=str(tmp_path))

    exit_code = cli_main(["doctor", "--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "agent-contracts doctor" in output
    assert "policy-load" in output


def test_cli_doctor_json_with_eval(tmp_path, capsys):
    write_scaffold(tmp_path, workspace_root=str(tmp_path))
    corpus = tmp_path / "eval.jsonl"
    corpus.write_text(
        '{"phase":"pre","tool":"write_file","params":{"path":"notes.md"},"expected_blocked":false}\n',
        encoding="utf-8",
    )

    exit_code = cli_main(["doctor", "--root", str(tmp_path), "--eval", str(corpus), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["passed"] is True
    assert any(check["name"] == "eval-corpus" for check in payload["checks"])
