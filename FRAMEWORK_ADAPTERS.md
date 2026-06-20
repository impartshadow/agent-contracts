# Framework adapters

`agent-contracts` is deliberately framework-agnostic. The integration point is
always the same: convert the tool call your framework is about to run into an
`ActionContext`, call `registry.enforce_pre(...)`, then dispatch only if the gate
passes.

These examples are adapter shapes, not new dependencies. Keep the package at the
shared boundary under your framework, not inside one prompt or one agent role.

## OpenAI function/tool calling

Gate the parsed tool call before invoking your local function map:

```python
from agent_contracts import ActionContext, BlockedAction, Registry, default_contracts

registry = Registry(default_contracts())

TOOLS = {
    "write_file": write_file,
    "send_email": send_email,
}


def dispatch_tool_call(tool_call):
    name = tool_call.function.name
    params = json.loads(tool_call.function.arguments or "{}")

    ctx = ActionContext(action="tool_call", tool=name, params=params)
    registry.enforce_pre(ctx)

    return TOOLS[name](**params)
```

Do not put the gate after the function call. The point is to block the side
effect before your local code touches the filesystem, network, database, or inbox.

Runnable example: [`examples/openai_tool_call_adapter.py`](examples/openai_tool_call_adapter.py).

## LangChain-style tool wrappers

Wrap every side-effecting tool with a small guard function:

```python
from agent_contracts import ActionContext, Registry, default_contracts

registry = Registry(default_contracts())


def guarded_tool(tool_name, fn):
    def wrapped(**kwargs):
        ctx = ActionContext(action="tool_call", tool=tool_name, params=kwargs)
        registry.enforce_pre(ctx)
        return fn(**kwargs)

    return wrapped


write_file_tool = guarded_tool("write_file", write_file)
run_shell_tool = guarded_tool("run_shell", run_shell)
```

If your agent can call both a shell tool and a file-write tool, gate both. A path
guard on `write_file` does not help if the agent can run `echo x > /etc/cron.d/x`
through shell.

## AutoGen-style function maps

Gate the function map instead of individual agents:

```python
from agent_contracts import ActionContext, Registry, default_contracts

registry = Registry(default_contracts())


class GuardedFunctionMap(dict):
    def __getitem__(self, name):
        fn = super().__getitem__(name)

        def guarded(**kwargs):
            ctx = ActionContext(action="tool_call", tool=name, params=kwargs)
            registry.enforce_pre(ctx)
            return fn(**kwargs)

        return guarded
```

The advantage of guarding the map is coverage. New agents inherit the boundary
automatically as long as they use the same function registry.

## CrewAI-style tools

Put the gate in the tool's `_run` method or in the common base class used by all
tools with side effects:

```python
from agent_contracts import ActionContext, Registry, default_contracts

registry = Registry(default_contracts())


class GuardedWriteFileTool(BaseTool):
    name = "write_file"

    def _run(self, path: str, content: str):
        params = {"path": path, "content": content}
        ctx = ActionContext(action="tool_call", tool=self.name, params=params)
        registry.enforce_pre(ctx)
        return write_file(path=path, content=content)
```

If the framework supports multiple execution modes, test every mode that can
reach the side effect. Contracts only work on paths they actually see.

## Raw CLI agents

For CLI agents, put the gate at the command runner and file writer boundary:

```python
from agent_contracts import ContractedToolRouter

router = ContractedToolRouter({
    "run_shell": run_shell,
    "write_file": write_file,
})

router.call("run_shell", {"cmd": "pytest -q"})
router.call("write_file", {"path": "notes.md", "content": "ship it\n"})
```

`ContractedToolRouter` ships in the package as a small reference dispatcher. Use
it directly for tiny agents, or copy the pattern into your existing router.

## Response boundary

Tool gates are not enough. Gate final user-visible text too:

```python
def emit(text, tools_called):
    result = registry.check_post(
        ActionContext(
            action="respond",
            response_text=text,
            tool_calls=tools_called,
        )
    )
    if result.blocked:
        raise RuntimeError(result.to_dict())
    return text
```

The default post checks catch likely secret leaks and warn on unsupported
completion claims. In production, log WARN results; they are often the first sign
that an agent is learning to claim work faster than it verifies work.

## Integration test template

Add one test proving a dangerous action never reaches the real function:

```python
import pytest

from agent_contracts import BlockedAction, ContractedToolRouter


def test_guard_blocks_before_side_effect():
    called = False

    def write_file(path, content):
        nonlocal called
        called = True

    router = ContractedToolRouter({"write_file": write_file})

    with pytest.raises(BlockedAction):
        router.call("write_file", {"path": "/etc/passwd", "content": "x"})

    assert called is False
```

That last assertion is the whole bar. If the underlying function ran, the guard
is in the wrong place.
