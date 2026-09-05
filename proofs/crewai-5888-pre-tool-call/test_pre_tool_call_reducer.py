"""Executable form of the authorization result contract at PRE_TOOL_CALL
(crewAIInc/crewAI#5888). Runs against the installed crewai package.

Documents what run_before_tool_call_hooks does with each hook outcome today.
The three EXPECTED_* names are the invariants safal207 stated (5462786066);
each assertion records the observed behaviour so a maintainer can see which
of the three the framework currently satisfies.
"""
import pytest
from crewai.hooks import HookAborted
from crewai.hooks import ToolCallHookContext
from crewai.hooks.tool_hooks import run_before_tool_call_hooks
import crewai.hooks as hooks

def _ctx():
    return ToolCallHookContext(tool_name="t", tool_input={"q": 1}, tool=None, agent=None, task=None, crew=None)

def _with_hook(fn):
    hooks.clear_all_global_hooks()
    hooks.register_before_tool_call_hook(fn)
    try:
        return run_before_tool_call_hooks(_ctx())   # True == blocked
    finally:
        hooks.clear_all_global_hooks()

def test_explicit_deny_via_false_blocks():
    assert _with_hook(lambda c: False) is True

def test_explicit_deny_via_hookaborted_blocks():
    def h(c): raise HookAborted("deny")
    assert _with_hook(h) is True

def test_explicit_allow_passes():
    assert _with_hook(lambda c: None) is False
    assert _with_hook(lambda c: True) is False

@pytest.mark.parametrize("err", [RuntimeError("provider down"), TimeoutError(), KeyError("policy")])
def test_provider_error_is_fail_open(err):
    # Invariant 3 (provider error -> zero tool-body calls) is NOT satisfied today:
    def h(c): raise err
    assert _with_hook(h) is False   # tool body would run

@pytest.mark.parametrize("result", [0, "false", "deny", {"allow": False}, [False]])
def test_unrecognized_result_is_treated_as_allow(result):
    # Invariant 3 (unrecognized result -> zero tool-body calls) is NOT satisfied today:
    # only the identity check `result is False` blocks (tool_hooks.py:148).
    assert _with_hook(lambda c: result) is False
