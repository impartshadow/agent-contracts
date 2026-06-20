"""Command-line demo for ``python -m agent_contracts``."""

from __future__ import annotations

from . import BlockedAction, ContractedToolRouter


def _write_file(path: str, content: str) -> str:
    return f"would write {len(content)} bytes to {path}"


def main() -> int:
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


if __name__ == "__main__":
    raise SystemExit(main())
