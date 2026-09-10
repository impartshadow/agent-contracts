# crewAI PRE_TOOL_CALL authorization conformance — independent read

Context: crewAIInc/crewAI#5888. Three executable checks, each against pinned inputs.

## Pinned inputs

| artifact | SHA-256 |
|---|---|
| `crewai-1.15.16-py3-none-any.whl` (PyPI) | `a93ae2c78b42dacdb932c2e4bbba2efb108ac610c23cf5453d8d59000858665b` |
| `crewai-1.15.20-py3-none-any.whl` (PyPI) | `8bf272a687ad3320b681f23a183a6ac445f2fa7fc78b52943b835acc2eb158d6` |
| `crewai-1.15.21-py3-none-any.whl` (PyPI) | `08ef2605260b0ffa7c54218fbcab8d3c4dc8d6307bd3b43513985529f6f666ab` |

1.15.21 is byte-identical to 1.15.20 in every file named below. Between 1.15.16 and 1.15.20,
`crewai/hooks/tool_hooks.py` and `crewai/utilities/tool_utils.py` are byte-identical;
`hooks/dispatch.py` differs only by a rename (`_source_name` → `source_name`) and a new
`EXECUTION_BOUNDARY_POINTS` constant. The fail-open semantics are unchanged.

## Files

- `test_pre_tool_call_reducer.py` — runs against the installed package. The three explicit cases pass;
  the eight fail-open cases are written as invariant 3 and marked `xfail(strict=True)`, so the run
  flips (XPASS -> fail) the day crewAI fails closed. Result on 1.15.20 and 1.15.21: 3 passed, 8 xfailed,
  which means: `False` and `HookAborted` block; a provider exception is fail-open; a hook returning
  `0`, `"false"`, `"deny"`, `{"allow": False}` or `[False]` is treated as allow, because the only
  blocking check is the identity test `result is False` (`tool_hooks.py:148`).
- `test_tool_body_capture.py` — static AST walk of the package. Every call site that can reach a
  tool body must be inside a function that dispatches `PRE_TOOL_CALL`, or be declared `NOT_COVERED`
  with a reason. Direct, unguarded sites found in both versions:
  `flow/runtime/_actions.py` (`ToolAction.run → tool.run`),
  `agents/agent_adapters/openai_agents/openai_agent_tool_adapter.py` (`tool._run`),
  `agents/agent_adapters/langgraph/langgraph_tool_adapter.py` (`tool.run`).
- `test_witness_binding.py` — extends the six-test witness suite (comment 5380834002) with the two
  construction-time checks proposed in comment 5390632120: config-perturbation replay and
  persisted-set-only reproducibility, each with a RED implementation.
- `report.txt` — the run output for the pins above.

## Reproduce

```
python -m venv v && v/bin/pip install crewai==1.15.20 pytest
v/bin/python -m pytest -q test_pre_tool_call_reducer.py test_witness_binding.py
python test_tool_body_capture.py "$(v/bin/python -c 'import crewai,os;print(os.path.dirname(crewai.__file__))')"
```

## Bounded claim

This reproduces the reducer and dispatch behaviour of the two pinned wheels and enumerates direct
tool-body call sites by a static heuristic (receiver named `tool*`, or `tool_func(**kwargs)`).
It is not a claim of complete capture: dynamic dispatch and third-party tool wrappers are outside
the heuristic. It says nothing about runtime correctness of any adapter or about production security.

## Patch

The three direct sites are covered by crewAIInc/crewAI#7372 (dispatch at the Flow tool action and both
adapters, with per-path reach tests). With that patch applied the static walk reports every site covered.
The reducer is untouched by that PR.
