"""Command-line entry point for ``python -m agent_contracts``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from . import ActionContext, BlockedAction, ContractedToolRouter, Registry, default_contracts
from .doctor import run_doctor
from .matrix import run_contract_matrix
from .policy import DEFAULT_POLICY_FILENAME, load_policy, write_policy
from .replay import load_jsonl, replay_file
from .eval import evaluate_records
from .sarif import replay_rows_to_sarif
from .scaffold import write_scaffold
from .score import score_repository


def _write_file(path: str, content: str) -> str:
    return f"would write {len(content)} bytes to {path}"


def _demo() -> int:
    """Run a small end-to-end contract demo."""

    router = ContractedToolRouter({"write_file": _write_file})

    print("agent-contracts demo")
    print("clean:", router.call("write_file", {"path": "notes.md", "content": "ship it\n"}))

    try:
        router.call(
            "write_file",
            {"path": "/etc/cron.d/backdoor", "content": "* * * * * root sh"},
        )
    except BlockedAction as exc:
        for violation in exc.violations:
            print(f"blocked: {violation.contract} - {violation.message}")

    result = router.check_response("Done, fixed it.")
    for violation in result.violations:
        print(f"warn: {violation.contract} - {violation.message}")

    return 0


def _load_json_object(raw: str, label: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} must be valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must decode to a JSON object")
    return value


def _build_context(args: argparse.Namespace) -> ActionContext:
    return ActionContext(
        action=args.action,
        tool=args.tool or "",
        params=_load_json_object(args.params_json, "--params-json"),
        response_text=args.response_text or "",
        user_message=args.user_message or "",
        files_written=json.loads(args.files_written_json),
        tool_calls=json.loads(args.tool_calls_json),
        edits_by_path=_load_json_object(args.edits_by_path_json, "--edits-by-path-json"),
        metadata=_load_json_object(args.metadata_json, "--metadata-json"),
    )


def _run_check(args: argparse.Namespace) -> int:
    ctx = _build_context(args)
    registry = load_policy(args.policy) if args.policy else Registry(default_contracts())

    result = registry.check_pre(ctx) if args.command == "check-pre" else registry.check_post(ctx)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        status = "blocked" if result.blocked else "warn" if result.violations else "pass"
        print(status)
        for violation in result.violations:
            print(f"{violation.severity.value}: {violation.contract} - {violation.message}")

    return 1 if result.blocked else 0


def _run_init(args: argparse.Namespace) -> int:
    try:
        path = write_policy(args.output, workspace_root=args.workspace, force=args.force)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"wrote {path}")
    return 0


def _run_matrix(args: argparse.Namespace) -> int:
    rows = run_contract_matrix()
    if args.json:
        print(json.dumps({"passed": all(row["passed"] for row in rows), "rows": rows}, indent=2))
    else:
        print("agent-contracts matrix")
        for row in rows:
            status = "pass" if row["passed"] else "fail"
            block_state = "block" if row["blocked"] else "warn"
            fired = ", ".join(row["fired_contracts"]) or "(none)"
            print(f"{status} {row['phase']:4} {block_state:5} {row['name']} -> {fired}")
    return 0 if all(row["passed"] for row in rows) else 1


def _run_bootstrap(args: argparse.Namespace) -> int:
    try:
        paths = write_scaffold(args.root, workspace_root=args.workspace, force=args.force)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for path in paths:
        print(f"wrote {path}")
    return 0


def _run_replay(args: argparse.Namespace) -> int:
    registry = load_policy(args.policy) if args.policy else Registry(default_contracts())
    try:
        rows = replay_file(args.path, registry)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    blocked_count = sum(1 for row in rows if row["blocked"])
    violation_count = sum(len(row["violations"]) for row in rows)
    expectations = {
        "blocks": args.expect_blocks,
        "violations": args.expect_violations,
    }
    has_expectations = args.expect_blocks is not None or args.expect_violations is not None
    expectations_matched = (
        (args.expect_blocks is None or blocked_count == args.expect_blocks)
        and (args.expect_violations is None or violation_count == args.expect_violations)
    )
    command_passed = expectations_matched if has_expectations else blocked_count == 0
    payload = {
        "passed": command_passed,
        "blocked_count": blocked_count,
        "violation_count": violation_count,
        "expectations": expectations,
        "rows": rows,
    }
    if args.sarif:
        print(json.dumps(replay_rows_to_sarif(rows, args.path), indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"replayed {len(rows)} records: "
            f"{blocked_count} blocked, {violation_count} violations"
        )
        for row in rows:
            if not row["violations"]:
                continue
            fired = ", ".join(v["contract"] for v in row["violations"])
            target = row["tool"] or row["action"] or "(unknown)"
            print(f"line {row['line']} {row['phase']} {target}: {fired}")

    if has_expectations:
        return 0 if command_passed else 1
    return 1 if blocked_count else 0


def _run_eval(args: argparse.Namespace) -> int:
    registry = load_policy(args.policy) if args.policy else Registry(default_contracts())
    try:
        payload = evaluate_records(load_jsonl(args.path), registry)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "evaluated "
            f"{payload['records']} records "
            f"({payload['labeled_records']} labeled): "
            f"tp={payload['true_positive']} "
            f"tn={payload['true_negative']} "
            f"fp={payload['false_positive']} "
            f"fn={payload['false_negative']} "
            f"precision={payload['precision']:.2f} "
            f"recall={payload['recall']:.2f}"
        )
        for miss in payload["contract_misses"]:
            missing = ", ".join(miss["missing_contracts"])
            fired = ", ".join(miss["fired_contracts"]) or "(none)"
            print(f"line {miss['line']} missing {missing}; fired {fired}")

    return 0 if payload["passed"] else 1


def _run_doctor(args: argparse.Namespace) -> int:
    try:
        payload = run_doctor(args.root, policy_path=args.policy, eval_path=args.eval)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "agent-contracts doctor: "
            f"{payload['required_passed']}/{payload['required_total']} required checks passed"
        )
        for check in payload["checks"]:
            status = "pass" if check["passed"] else "fail" if check["required"] else "skip"
            path = f" ({check['path']})" if check.get("path") else ""
            print(f"{status} {check['name']}{path}: {check['message']}")

    return 0 if payload["passed"] else 1


def _run_score(args: argparse.Namespace) -> int:
    payload = score_repository(
        args.root,
        policy_path=args.policy,
        eval_path=args.eval,
        replay_path=args.replay,
    )

    if args.badge:
        print(payload["badge_markdown"])
        return 0
    elif args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"agent reliability: {payload['score']}/100 ({payload['grade']})")
        for component in payload["components"]:
            print(
                f"{component['points']:>2}/{component['max_points']} "
                f"{component['name']}"
            )
        print(payload["badge_markdown"])

    return 0 if payload["passed"] else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-contracts",
        description="Run deterministic pre/post-condition checks for agent actions.",
    )
    subparsers = parser.add_subparsers(dest="command")

    for command in ("check-pre", "check-post"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--action", default="tool_call" if command == "check-pre" else "respond")
        sub.add_argument("--tool")
        sub.add_argument("--params-json", default="{}")
        sub.add_argument("--response-text")
        sub.add_argument("--user-message")
        sub.add_argument("--files-written-json", default="[]")
        sub.add_argument("--tool-calls-json", default="[]")
        sub.add_argument("--edits-by-path-json", default="{}")
        sub.add_argument("--metadata-json", default="{}")
        sub.add_argument("--policy", help="optional policy file generated by agent-contracts init")
        sub.add_argument("--json", action="store_true")

    init = subparsers.add_parser("init", help="write a starter agent-contracts policy file")
    init.add_argument("--output", default=DEFAULT_POLICY_FILENAME)
    init.add_argument("--workspace", default=".")
    init.add_argument("--force", action="store_true")

    matrix = subparsers.add_parser("matrix", help="run canonical examples for every built-in contract")
    matrix.add_argument("--json", action="store_true")

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help="write policy, adapter, and CI scaffold into a repository",
    )
    bootstrap.add_argument("--root", default=".")
    bootstrap.add_argument("--workspace", default=".")
    bootstrap.add_argument("--force", action="store_true")

    replay = subparsers.add_parser(
        "replay",
        help="replay JSONL action records through a policy or the default contracts",
    )
    replay.add_argument("path")
    replay.add_argument("--policy", help="optional policy file generated by agent-contracts init")
    replay.add_argument("--json", action="store_true")
    replay.add_argument("--sarif", action="store_true", help="emit SARIF 2.1.0 for code scanning")
    replay.add_argument("--expect-blocks", type=int, help="pass only if this many records block")
    replay.add_argument(
        "--expect-violations",
        type=int,
        help="pass only if this many total violations fire",
    )

    eval_parser = subparsers.add_parser(
        "eval",
        help="evaluate labeled JSONL records against a policy or the default contracts",
    )
    eval_parser.add_argument("path")
    eval_parser.add_argument("--policy", help="optional policy file generated by agent-contracts init")
    eval_parser.add_argument("--json", action="store_true")

    doctor = subparsers.add_parser(
        "doctor",
        help="inspect repository adoption wiring without changing files",
    )
    doctor.add_argument("--root", default=".")
    doctor.add_argument("--policy", help="policy path, defaults to <root>/agent-contracts.yml")
    doctor.add_argument("--eval", help="optional labeled JSONL corpus to evaluate")
    doctor.add_argument("--json", action="store_true")

    score = subparsers.add_parser(
        "score",
        help="score repository agent reliability and emit badge-ready output",
    )
    score.add_argument("--root", default=".")
    score.add_argument("--policy", help="policy path, defaults to <root>/agent-contracts.yml")
    score.add_argument("--eval", help="optional labeled JSONL corpus to evaluate")
    score.add_argument("--replay", help="optional historical/incident JSONL log to replay")
    score.add_argument("--json", action="store_true")
    score.add_argument("--badge", action="store_true", help="print markdown badge only")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Run the demo or a contract check."""

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return _demo()

    parser = _parser()
    args = parser.parse_args(argv)
    if args.command in {"check-pre", "check-post"}:
        return _run_check(args)
    if args.command == "init":
        return _run_init(args)
    if args.command == "matrix":
        return _run_matrix(args)
    if args.command == "bootstrap":
        return _run_bootstrap(args)
    if args.command == "replay":
        return _run_replay(args)
    if args.command == "eval":
        return _run_eval(args)
    if args.command == "doctor":
        return _run_doctor(args)
    if args.command == "score":
        return _run_score(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
