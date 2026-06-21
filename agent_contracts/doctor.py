"""Read-only adoption diagnostics for a repository using agent-contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union

from .eval import evaluate_records
from .matrix import run_contract_matrix
from .policy import DEFAULT_POLICY_FILENAME, load_policy
from .replay import load_jsonl
from .scaffold import DEFAULT_PRE_COMMIT_PATH, DEFAULT_SCAFFOLD_DIR, DEFAULT_WORKFLOW_PATH


def _check_file(path: Path, label: str) -> dict[str, Any]:
    return {
        "name": label,
        "path": path.as_posix(),
        "passed": path.exists(),
        "required": True,
        "message": "present" if path.exists() else "missing",
    }


def _optional_file(path: Path, label: str) -> dict[str, Any]:
    return {
        "name": label,
        "path": path.as_posix(),
        "passed": path.exists(),
        "required": False,
        "message": "present" if path.exists() else "not configured",
    }


def run_doctor(
    root: Union[str, Path] = ".",
    *,
    policy_path: Union[str, Path, None] = None,
    eval_path: Union[str, Path, None] = None,
) -> dict[str, Any]:
    """Return a read-only adoption report for ``root``."""

    base = Path(root)
    if policy_path:
        policy = Path(policy_path)
        if not policy.is_absolute():
            policy = base / policy
    else:
        policy = base / DEFAULT_POLICY_FILENAME
    checks: list[dict[str, Any]] = []

    checks.append(_check_file(policy, "policy"))
    checks.append(_check_file(base / DEFAULT_SCAFFOLD_DIR / "adapter.py", "adapter"))
    checks.append(_check_file(base / DEFAULT_WORKFLOW_PATH, "github-actions"))
    checks.append(_optional_file(base / DEFAULT_PRE_COMMIT_PATH, "pre-commit"))

    matrix_rows = run_contract_matrix()
    checks.append(
        {
            "name": "built-in-matrix",
            "path": None,
            "passed": all(row["passed"] for row in matrix_rows),
            "required": True,
            "message": "all built-in contracts fired" if all(row["passed"] for row in matrix_rows) else "matrix failed",
        }
    )

    policy_loaded = False
    if policy.exists():
        try:
            load_policy(policy)
            policy_loaded = True
            checks.append(
                {
                    "name": "policy-load",
                    "path": policy.as_posix(),
                    "passed": True,
                    "required": True,
                    "message": "loaded",
                }
            )
        except Exception as exc:  # pragma: no cover - defensive diagnostic surface
            checks.append(
                {
                    "name": "policy-load",
                    "path": policy.as_posix(),
                    "passed": False,
                    "required": True,
                    "message": str(exc),
                }
            )

    if eval_path:
        evaluation = Path(eval_path)
        if not evaluation.is_absolute():
            evaluation = base / evaluation
        if evaluation.exists():
            registry = load_policy(policy) if policy_loaded else None
            if registry is None:
                checks.append(
                    {
                        "name": "eval-corpus",
                        "path": evaluation.as_posix(),
                        "passed": False,
                        "required": False,
                        "message": "policy did not load",
                    }
                )
            else:
                payload = evaluate_records(load_jsonl(evaluation), registry)
                checks.append(
                    {
                        "name": "eval-corpus",
                        "path": evaluation.as_posix(),
                        "passed": payload["passed"],
                        "required": False,
                        "message": (
                            f"tp={payload['true_positive']} tn={payload['true_negative']} "
                            f"fp={payload['false_positive']} fn={payload['false_negative']}"
                        ),
                        "metrics": payload,
                    }
                )
        else:
            checks.append(_optional_file(evaluation, "eval-corpus"))

    required = [check for check in checks if check["required"]]
    passed_required = sum(1 for check in required if check["passed"])
    passed_all = sum(1 for check in checks if check["passed"])
    required_ok = passed_required == len(required)
    optional_failures = [check for check in checks if not check["required"] and not check["passed"]]

    return {
        "passed": required_ok and not any(
            check["name"] == "eval-corpus" and not check["passed"] for check in checks
        ),
        "required_passed": passed_required,
        "required_total": len(required),
        "checks_passed": passed_all,
        "checks_total": len(checks),
        "optional_not_configured": len(optional_failures),
        "checks": checks,
    }
