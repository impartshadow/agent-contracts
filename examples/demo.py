"""A runnable demo: wrap a fake agent tool call in a contract gate.

Run it::

    python examples/demo.py

You'll see a dangerous write get blocked before it executes, a leaked secret
caught on the way out, and a clean call sail through.
"""

from agent_contracts import ActionContext, BlockedAction, Registry, default_contracts


def fake_write_file(path: str, content: str) -> str:
    # pretend this touches the real filesystem
    return f"wrote {len(content)} bytes to {path}"


def guarded_write(registry: Registry, path: str, content: str) -> str:
    ctx = ActionContext(
        action="tool_call",
        tool="write_file",
        params={"path": path, "content": content},
    )
    registry.enforce_pre(ctx)  # raises BlockedAction if a contract blocks
    return fake_write_file(path, content)


def main() -> None:
    registry = Registry(default_contracts())

    print("1. clean write to the workspace:")
    print("  ", guarded_write(registry, "report.md", "# Findings\n"))

    print("\n2. write to a protected system path:")
    try:
        guarded_write(registry, "/etc/cron.d/backdoor", "* * * * * root sh -c ...")
    except BlockedAction as e:
        for v in e.violations:
            print(f"   BLOCKED [{v.contract}] {v.message}")

    print("\n3. a response that leaks a secret:")
    ctx = ActionContext(
        action="respond",
        response_text="Sure, the key is AKIAIOSFODNN7EXAMPLE — paste that in.",
    )
    post = registry.check_post(ctx)
    for v in post.violations:
        print(f"   CAUGHT  [{v.contract}] {v.message}")


if __name__ == "__main__":
    main()
