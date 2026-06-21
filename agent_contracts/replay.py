"""Replay JSONL action logs through an agent-contracts registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Union

from .core import ActionContext, Registry


def context_from_record(record: dict[str, Any]) -> ActionContext:
    """Build an ActionContext from one JSON object."""

    return ActionContext(
        action=str(record.get("action") or ""),
        tool=str(record.get("tool") or ""),
        params=dict(record.get("params") or {}),
        response_text=str(record.get("response_text") or ""),
        user_message=str(record.get("user_message") or ""),
        files_written=list(record.get("files_written") or []),
        tool_calls=list(record.get("tool_calls") or []),
        edits_by_path=dict(record.get("edits_by_path") or {}),
        metadata=dict(record.get("metadata") or {}),
    )


def load_jsonl(path: Union[str, Path]) -> list[dict[str, Any]]:
    """Read newline-delimited JSON objects from ``path``."""

    records: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected a JSON object")
        value.setdefault("_line", line_no)
        records.append(value)
    return records


def replay_records(records: Iterable[dict[str, Any]], registry: Registry) -> list[dict[str, Any]]:
    """Run each record through the requested phase and return serializable rows."""

    rows: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        phase = str(record.get("phase") or "pre").lower()
        if phase not in {"pre", "post"}:
            raise ValueError(f"record {index}: phase must be 'pre' or 'post'")

        normalized = dict(record)
        normalized.setdefault("action", "tool_call" if phase == "pre" else "respond")
        ctx = context_from_record(normalized)
        result = registry.check_pre(ctx) if phase == "pre" else registry.check_post(ctx)
        rows.append(
            {
                "index": index,
                "line": record.get("_line", index),
                "phase": phase,
                "action": ctx.action,
                "tool": ctx.tool,
                "passed": result.passed,
                "blocked": result.blocked,
                "violations": [violation.to_dict() for violation in result.violations],
            }
        )
    return rows


def replay_file(path: Union[str, Path], registry: Registry) -> list[dict[str, Any]]:
    """Replay all JSONL records in a file through a registry."""

    return replay_records(load_jsonl(path), registry)
