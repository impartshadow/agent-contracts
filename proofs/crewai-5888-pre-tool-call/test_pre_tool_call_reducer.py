"""Executable form of the authorization result contract at PRE_TOOL_CALL
(crewAIInc/crewAI#5888). Runs against the installed crewai package.

Documents what run_before_tool_call_hooks does with each hook outcome today.
The three EXPECTED_* names are the invariants safal207 stated (5462786066);
the fail-open cases are written as the invariant and marked xfail(strict=True),
so the run flips the day the framework fails closed (see FAIL_OPEN below).
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

# Acceptance tests for invariant 3, stated as the invariant rather than as today's
# behaviour (rafaelasor, crewAI#5888 comment 5556597911). Each is xfail(strict=True):
# the suite stays green while crewAI is fail-open at tool_hooks.py:148, and the
# moment a release fails closed these XPASS, which fails the run until the marker
# is removed. That flip is the acceptance event.
FAIL_OPEN = "crewai fails open: only `result is False` or HookAborted blocks (tool_hooks.py:148); a hook exception is swallowed"

@pytest.mark.xfail(strict=True, reason=FAIL_OPEN)
@pytest.mark.parametrize("err", [RuntimeError("provider down"), TimeoutError(), KeyError("policy")])
def test_provider_error_blocks_the_call(err):
    # Invariant 3: provider error -> zero tool-body calls.
    def h(c): raise err
    assert _with_hook(h) is True

@pytest.mark.xfail(strict=True, reason=FAIL_OPEN)
@pytest.mark.parametrize("result", [0, "false", "deny", {"allow": False}, [False]])
def test_unrecognized_result_blocks_the_call(result):
    # Invariant 3: an unrecognised verdict -> zero tool-body calls.
    assert _with_hook(lambda c: result) is True
