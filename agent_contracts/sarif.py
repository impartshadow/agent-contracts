"""SARIF rendering for contract replay results."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union


def _level(severity: str) -> str:
    if severity == "block":
        return "error"
    return "warning"


def replay_rows_to_sarif(rows: list[dict[str, Any]], source_path: Union[str, Path]) -> dict[str, Any]:
    """Render replay rows as a SARIF 2.1.0 payload."""

    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    uri = Path(source_path).as_posix()

    for row in rows:
        for violation in row["violations"]:
            rule_id = str(violation["contract"])
            rules.setdefault(
                rule_id,
                {
                    "id": rule_id,
                    "name": rule_id,
                    "shortDescription": {"text": rule_id},
                    "help": {"text": str(violation.get("recovery") or "")},
                },
            )
            results.append(
                {
                    "ruleId": rule_id,
                    "level": _level(str(violation.get("severity") or "")),
                    "message": {"text": str(violation["message"])},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": uri},
                                "region": {"startLine": int(row["line"])},
                            }
                        }
                    ],
                    "properties": {
                        "phase": row["phase"],
                        "action": row["action"],
                        "tool": row["tool"],
                        "blocking": bool(violation["blocking"]),
                    },
                }
            )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "agent-contracts",
                        "informationUri": "https://github.com/impartshadow/agent-contracts",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }
