# MCP Adapter

MCP is useful because tools and auth can sit outside the model context. That does
not make every tool call safe. The contract boundary still belongs immediately
before the authenticated tool executes.

The adapter shape is the same for a local tool server, remote MCP server, or
gateway:

```python
from agent_contracts import ActionContext, Registry, default_contracts

registry = Registry(default_contracts())


def dispatch_mcp_tool_call(name, arguments):
    ctx = ActionContext(action="tool_call", tool=name, params=arguments)
    registry.enforce_pre(ctx)
    return dispatch_to_real_mcp_tool(name, arguments)
```

Runnable no-SDK example:

```bash
python examples/mcp_tool_adapter.py
```

## Gateway rule

Put contracts in the narrowest shared dispatcher that every side-effecting MCP
tool crosses:

| MCP surface | Contract placement |
|---|---|
| Local MCP server | Before the local handler function runs |
| Remote MCP client | Before sending the tool-call request |
| Tool gateway/proxy | Before forwarding to the upstream tool server |
| Multi-agent runtime | In the shared tool registry, not inside each prompt |

## What to pass into `ActionContext`

| Field | MCP source |
|---|---|
| `action` | `"tool_call"` |
| `tool` | MCP tool name |
| `params` | tool call arguments |
| `metadata` | account, workspace, risk tier, tenant, environment |
| `tool_calls` | calls already made this turn |
| `edits_by_path` | write counts tracked by the runtime |

## Failure mode this prevents

Without a deterministic gate, the model can ask an authenticated MCP server to do
the wrong thing with valid credentials: write outside the workspace, run a shell
command with too much blast radius, leak a token into a ticket, or call a tool the
current role should not have.

Contracts do not replace MCP auth isolation. They add the action boundary MCP
does not define by itself: this authenticated call is well-formed, but should it
be allowed right now?
