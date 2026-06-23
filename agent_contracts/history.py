"""Persistent scan history for the public agent-governance leaderboard.

The leaderboard is only a *living* index if every scan is recorded and the next
scan can be diffed against the last. This module owns that durable record: an
append-only JSONL log where each line is one project's score from one scan run,
tagged with the run timestamp and the exact commit SHA that was scored.

A score with no provenance is a vibe. Every row here answers "scored what, when,
at which commit" so a regression ("LangGraph dropped 7 points in v0.4") is always
reproducible from a clean clone at the recorded SHA.

Schema (one JSON object per line)::

    {
      "run_id": "2026-06-23T01:40:12Z",   # shared by all rows in one scan run
      "scanned_at": "2026-06-23T01:40:12Z",
      "project": "langchain-ai/langgraph",
      "scanned_sha": "a1b2c3d...",         # HEAD of the clone, or null if unknown
      "score": 100,
      "grade": "A",
      "components": {"tests_and_ci": 20, "tool_governance": 20, ...}
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Union

DEFAULT_HISTORY_FILENAME = "leaderboard_history.jsonl"


def utc_now_iso() -> str:
    """UTC timestamp, second precision, trailing Z — stable for run_id sorting."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _components_map(payload: dict[str, Any]) -> dict[str, int]:
    return {c["name"]: c["points"] for c in payload.get("components", [])}


def record_from_payload(
    payload: dict[str, Any],
    *,
    run_id: str,
    scanned_at: str,
    scanned_sha: Optional[str],
) -> dict[str, Any]:
    """Flatten a ``scan_repository`` payload into one durable history row."""

    return {
        "run_id": run_id,
        "scanned_at": scanned_at,
        "project": payload["project"],
        "scanned_sha": scanned_sha,
        "score": payload["score"],
        "grade": payload["grade"],
        "components": _components_map(payload),
    }


def append_run(
    history_path: Union[str, Path],
    rows: Iterable[dict[str, Any]],
    *,
    run_id: Optional[str] = None,
    scanned_at: Optional[str] = None,
    shas: Optional[dict[str, Optional[str]]] = None,
) -> str:
    """Append one scan run to the history log. Returns the run_id used.

    ``rows`` are ``scan_repository`` payloads, each carrying a ``project`` key.
    ``shas`` maps project -> scanned commit SHA (missing => null).
    """

    run_id = run_id or utc_now_iso()
    scanned_at = scanned_at or run_id
    shas = shas or {}

    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for payload in rows:
            record = record_from_payload(
                payload,
                run_id=run_id,
                scanned_at=scanned_at,
                scanned_sha=shas.get(payload["project"]),
            )
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    return run_id


def load_history(history_path: Union[str, Path]) -> list[dict[str, Any]]:
    """Load every recorded scan row. Tolerates a missing file (returns [])."""

    path = Path(history_path)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            # A corrupt line should not blind us to the rest of the history.
            continue
    return records


def run_ids(history: list[dict[str, Any]]) -> list[str]:
    """Distinct run_ids, oldest first (lexicographic == chronological for UTC Z)."""

    return sorted({r["run_id"] for r in history if r.get("run_id")})


def run_map(history: list[dict[str, Any]], run_id: str) -> dict[str, dict[str, Any]]:
    """All rows from one run, keyed by project."""

    return {r["project"]: r for r in history if r.get("run_id") == run_id}


def previous_run_map(
    history: list[dict[str, Any]], before_run_id: str
) -> dict[str, dict[str, Any]]:
    """Project -> record for the most recent run strictly older than ``before_run_id``.

    Empty dict when there is no prior run (the very first scan has nothing to
    diff against).
    """

    prior = [rid for rid in run_ids(history) if rid < before_run_id]
    if not prior:
        return {}
    return run_map(history, prior[-1])
