"""Tiny local benchmark for the default contract set.

This is not a scientific benchmark. It is a smoke test for the claim that these
checks are cheap enough to run at every tool boundary.
"""

from __future__ import annotations

import argparse
import time
from typing import Optional

from agent_contracts import ActionContext, Registry, default_contracts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark default agent-contract checks.")
    parser.add_argument("--iterations", type=int, default=10_000)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.iterations <= 0:
        raise SystemExit("--iterations must be positive")

    registry = Registry(default_contracts())
    clean = ActionContext(
        action="tool_call",
        tool="write_file",
        params={"path": "notes.md", "content": "ok"},
    )
    blocked = ActionContext(
        action="tool_call",
        tool="run_shell",
        params={"cmd": "sudo systemctl restart prod"},
    )
    response = ActionContext(action="respond", response_text="Done, fixed it.")

    start = time.perf_counter()
    blocked_count = 0
    warn_count = 0
    for _ in range(args.iterations):
        if registry.check_pre(clean).blocked:
            blocked_count += 1
        if registry.check_pre(blocked).blocked:
            blocked_count += 1
        warn_count += len(registry.check_post(response).violations)
    elapsed = time.perf_counter() - start
    checks = args.iterations * 3

    print(f"checks: {checks}")
    print(f"elapsed_seconds: {elapsed:.6f}")
    print(f"avg_microseconds_per_check: {(elapsed / checks) * 1_000_000:.3f}")
    print(f"blocked_results: {blocked_count}")
    print(f"warning_results: {warn_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
