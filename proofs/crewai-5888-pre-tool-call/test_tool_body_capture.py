"""Static complete-capture check for PRE_TOOL_CALL (crewAIInc/crewAI#5888).

Walks the installed crewai package and lists every call site that can reach a
tool body (BaseTool.run / _run / invoke / ToolUsage.use). Each site must be
either (a) inside a function that dispatches run_before_tool_call_hooks before
the body, or (b) explicitly declared NOT_COVERED with a reason. Anything else
fails. This is the framework-side assertion an adapter cannot make.
"""
import ast, os, sys, pathlib

PKG = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__import__("crewai").__file__))
BODY_CALLS = {"run", "_run", "use", "invoke"}
HOOK_FN = "run_before_tool_call_hooks"

GUARDED = {        # file -> functions that dispatch PRE_TOOL_CALL before reaching the body
    "utilities/tool_utils.py": {"aexecute_tool_and_check_finality", "execute_tool_and_check_finality"},
    "agents/crew_agent_executor.py": {"_execute_native_tool_call"},
    "experimental/agent_executor.py": {"_execute_native_tool_call"},
    "utilities/agent_utils.py": {"execute_single_native_tool_call"},
}
NOT_COVERED = {    # file -> reason
    "flow/runtime/_actions.py": "Flow ToolAction.run calls BaseTool.run directly; no PRE_TOOL_CALL",
    "agents/agent_adapters/openai_agents/openai_agent_tool_adapter.py": "adapter calls tool._run directly",
    "agents/agent_adapters/langgraph/langgraph_tool_adapter.py": "adapter calls tool.run directly",
    "tools/tool_usage.py": "ToolUsage._use is the body; guarded by its callers in tool_utils",
    "tools/structured_tool.py": "_run -> invoke inside the same tool object",
    "tools/base_tool.py": "run -> _run inside the same tool object",
    "tools/mcp_tool_wrapper.py": "_run -> _run_async inside the same tool object",
}

def receiver_looks_like_tool(node):
    f = node.func
    if isinstance(f, ast.Name):                       # native paths: tool_func(**args_dict)
        return f.id in {"tool_func", "func"} and any(isinstance(k, ast.keyword) and k.arg is None for k in node.keywords)
    if not isinstance(f, ast.Attribute):
        return False
    src = ast.unparse(f.value)
    return any(k in src for k in ("tool", "self")) and f.attr in BODY_CALLS

def guarded_functions(tree):
    out = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(isinstance(n, ast.Name) and n.id == HOOK_FN for n in ast.walk(fn)):
                out.add(fn.name)
    return out

failures, rows = [], []
for path in sorted(PKG.rglob("*.py")):
    rel = str(path.relative_to(PKG))
    tree = ast.parse(path.read_text())
    guarded = guarded_functions(tree)
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and receiver_looks_like_tool(node):
                src = ast.unparse(node.func)
                if isinstance(node.func, ast.Attribute) and "tool" not in src.rsplit(".", 1)[0]:
                    continue
                status = ("covered" if fn.name in guarded or fn.name in GUARDED.get(rel, set())
                          else "NOT_COVERED" if rel in NOT_COVERED else "UNDECLARED")
                rows.append((rel, node.lineno, fn.name, src, status))
                if status == "UNDECLARED":
                    failures.append((rel, node.lineno, fn.name, src))

seen = {}
for r in rows:
    seen[(r[0], r[1])] = r
rows = sorted(seen.values())
failures = [(r[0], r[1], r[2], r[3]) for r in rows if r[4] == "UNDECLARED"]
for r in rows:
    print("%-70s %5d  %-32s %-28s %s" % r)
print("\nhook sites:", sorted((f, fn) for f, g in GUARDED.items() for fn in g))
print("UNDECLARED:", failures)
sys.exit(1 if failures else 0)
