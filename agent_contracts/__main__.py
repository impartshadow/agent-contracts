"""Command-line entry point for ``python -m agent_contracts``."""

from __future__ import annotations

import argparse
import json
import sys

from . import ActionContext, BlockedAction, ContractedToolRouter, Registry, default_contracts
from .policy import DEFAULT_POLICY_FILENAME, write_policy


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
    registry = Registry(default_contracts())

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
        sub.add_argument("--json", action="store_true")

    init = subparsers.add_parser("init", help="write a starter agent-contracts policy file")
    init.add_argument("--output", default=DEFAULT_POLICY_FILENAME)
    init.add_argument("--workspace", default=".")
    init.add_argument("--force", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
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

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
