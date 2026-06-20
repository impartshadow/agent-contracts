"""Render the contract demo to a self-contained SVG terminal cast.

Runs the real registry against three live calls — a clean write, a blocked
write to a protected path, and a secret caught on the way out — and exports the
colored terminal output to docs/demo.svg. No external upload, no account.

    python examples/render_demo_svg.py
"""

from pathlib import Path

from rich.console import Console

from agent_contracts import ActionContext, BlockedAction, Registry, default_contracts


def guarded_write(registry, console, path, content):
    ctx = ActionContext(
        action="tool_call",
        tool="write_file",
        params={"path": path, "content": content},
    )
    registry.enforce_pre(ctx)
    return f"wrote {len(content)} bytes to {path}"


def main() -> None:
    console = Console(record=True, width=92)
    registry = Registry(default_contracts())

    console.print("[bold white]$ python -m my_agent[/]  [dim]# every tool call passes through the registry[/]")
    console.print()

    console.print("[bold]› agent writes a report to the workspace[/]")
    out = guarded_write(registry, console, "report.md", "# Findings\n")
    console.print(f"  [green]✓ allowed[/]  {out}")
    console.print()

    console.print("[bold]› agent tries to drop a backdoor in a system path[/]")
    try:
        guarded_write(registry, console, "/etc/cron.d/backdoor", "* * * * * root sh -c ...")
    except BlockedAction as e:
        for v in e.violations:
            console.print(f"  [bold red]✗ BLOCKED[/] [yellow]{v.contract}[/]  {v.message}")
    console.print()

    console.print("[bold]› agent's reply leaks an access key[/]")
    ctx = ActionContext(
        action="respond",
        response_text="Sure — the key is AKIAIOSFODNN7EXAMPLE, paste that in.",
    )
    post = registry.check_post(ctx)
    for v in post.violations:
        console.print(f"  [bold red]✗ CAUGHT[/]  [yellow]{v.contract}[/]  {v.message}")
    console.print()

    console.print("[dim]no model in the loop — every decision is a plain Python function[/]")

    out_path = Path(__file__).resolve().parent.parent / "docs" / "demo.svg"
    out_path.parent.mkdir(exist_ok=True)
    console.save_svg(str(out_path), title="agent-contracts")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
