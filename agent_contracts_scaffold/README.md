# agent-contracts scaffold

Generated files:

- `agent-contracts.yml` - local policy, workspace root `/home/agentshadow/agent-contracts`
- `.github/workflows/agent-contracts.yml` - CI proof that the built-in matrix and one workspace escape check fire
- `.pre-commit-config.yaml` - optional local hook that runs the matrix and doctor before commits
- `agent_contracts_scaffold/adapter.py` - importable helper for the shared tool dispatcher

Wire the adapter at the one place where your agent dispatches tools:

```python
from agent_contracts_scaffold.adapter import gate_tool_call, gate_response

gate_tool_call(tool_name, tool_params, edits_by_path=edit_counts)
result = run_tool(tool_name, tool_params)
warnings = gate_response(agent_reply, tool_calls=[tool_name])
```

The adoption bar is simple: a blocked tool call must fail before the side effect
runs. If the contract only logs after the tool runs, it is monitoring, not a
boundary.
