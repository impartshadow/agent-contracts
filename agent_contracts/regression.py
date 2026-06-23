"""Diff two leaderboard scan runs and surface what changed.

A static scorecard rots the moment a framework ships a release. The value of a
*continuous* index is the delta: "secret_safety dropped 7 points in this repo
since last scan." This module turns two history snapshots into a ranked list of
changes — regressions first, because a guardrail that disappeared is news, while
a guardrail that appeared is merely nice.

It makes no network calls and reads no files; it operates purely on the records
produced by :mod:`agent_contracts.history`, so it is trivially testable.
"""

from __future__ import annotations

from typing import Any, Optional

# Classification of a project's movement between two runs.
NEW = "new"
REGRESSION = "regression"
IMPROVEMENT = "improvement"
UNCHANGED = "unchanged"

# Severity of a change, for sorting and for deciding what is worth a maintainer
# touch / a content beat.
CRITICAL = "critical"  # grade dropped, or score fell >= GRADE_BAND points
WARN = "warn"  # score fell by a smaller margin, or a single dimension regressed
INFO = "info"  # improvements / cosmetic movement

_GRADE_BAND = 10


def _dimension_deltas(
    prev: dict[str, int], curr: dict[str, int]
) -> list[dict[str, Any]]:
    """Per-dimension point movement, only for dimensions that actually moved."""

    deltas: list[dict[str, Any]] = []
    for name in sorted(set(prev) | set(curr)):
        before = prev.get(name, 0)
        after = curr.get(name, 0)
        if before != after:
            deltas.append(
                {"name": name, "from": before, "to": after, "delta": after - before}
            )
    return deltas


def diff_project(
    prev: Optional[dict[str, Any]], curr: dict[str, Any]
) -> dict[str, Any]:
    """Compare one project's previous record with its current record."""

    project = curr["project"]
    curr_components = curr.get("components", {})

    if prev is None:
        return {
            "project": project,
            "classification": NEW,
            "severity": INFO,
            "score_from": None,
            "score_to": curr["score"],
            "score_delta": None,
            "grade_from": None,
            "grade_to": curr["grade"],
            "grade_changed": True,
            "dimension_deltas": [],
            "scanned_sha": curr.get("scanned_sha"),
        }

    prev_components = prev.get("components", {})
    score_delta = curr["score"] - prev["score"]
    dim_deltas = _dimension_deltas(prev_components, curr_components)
    any_dim_drop = any(d["delta"] < 0 for d in dim_deltas)
    grade_changed = prev["grade"] != curr["grade"]
    grade_dropped = grade_changed and curr["grade"] > prev["grade"]  # "B" > "A"

    if score_delta < 0 or any_dim_drop:
        classification = REGRESSION
    elif score_delta > 0:
        classification = IMPROVEMENT
    else:
        classification = UNCHANGED

    if classification == REGRESSION and (grade_dropped or score_delta <= -_GRADE_BAND):
        severity = CRITICAL
    elif classification == REGRESSION:
        severity = WARN
    else:
        severity = INFO

    return {
        "project": project,
        "classification": classification,
        "severity": severity,
        "score_from": prev["score"],
        "score_to": curr["score"],
        "score_delta": score_delta,
        "grade_from": prev["grade"],
        "grade_to": curr["grade"],
        "grade_changed": grade_changed,
        "dimension_deltas": dim_deltas,
        "scanned_sha": curr.get("scanned_sha"),
        "prev_scanned_sha": prev.get("scanned_sha"),
    }


_SEVERITY_RANK = {CRITICAL: 0, WARN: 1, INFO: 2}
_CLASS_RANK = {REGRESSION: 0, NEW: 1, IMPROVEMENT: 2, UNCHANGED: 3}


def diff_runs(
    prev_map: dict[str, dict[str, Any]], curr_map: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Diff every project in the current run against the previous run.

    Sorted regressions-first (by severity, then by magnitude of the drop), so the
    head of the list is exactly what a maintainer or a "what changed" post should
    lead with.
    """

    changes = [
        diff_project(prev_map.get(project), curr)
        for project, curr in curr_map.items()
    ]

    def sort_key(c: dict[str, Any]) -> tuple:
        delta = c["score_delta"] if c["score_delta"] is not None else 0
        return (
            _CLASS_RANK[c["classification"]],
            _SEVERITY_RANK[c["severity"]],
            delta,  # most-negative (worst regression) first within a tier
            c["project"],
        )

    return sorted(changes, key=sort_key)


def regressions(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in changes if c["classification"] == REGRESSION]


def summarize(changes: list[dict[str, Any]]) -> dict[str, int]:
    counts = {REGRESSION: 0, IMPROVEMENT: 0, NEW: 0, UNCHANGED: 0}
    for c in changes:
        counts[c["classification"]] += 1
    return counts


def trend_cell(change: Optional[dict[str, Any]]) -> str:
    """Compact trend indicator for a leaderboard row (e.g. '▼ -7', '▲ +3', '–')."""

    if change is None or change["classification"] in (UNCHANGED,):
        return "–"
    if change["classification"] == NEW:
        return "new"
    delta = change["score_delta"]
    if delta is None or delta == 0:
        return "–"
    arrow = "▲" if delta > 0 else "▼"
    return f"{arrow} {delta:+d}"


def _fmt_dims(dim_deltas: list[dict[str, Any]]) -> str:
    if not dim_deltas:
        return ""
    parts = [f"{d['name']} {d['from']}→{d['to']}" for d in dim_deltas]
    return "; ".join(parts)


def render_regressions_markdown(
    changes: list[dict[str, Any]],
    *,
    run_id: str,
    prev_run_id: Optional[str],
) -> str:
    """Human-readable changelog for a scan run — the content/news artifact."""

    counts = summarize(changes)
    lines = [
        "# Agent Governance Index — Change Report",
        "",
        f"Run `{run_id}`"
        + (f" vs previous `{prev_run_id}`" if prev_run_id else " (baseline — no prior run)"),
        "",
        f"**{counts[REGRESSION]} regressions · {counts[IMPROVEMENT]} improvements · "
        f"{counts[NEW]} new · {counts[UNCHANGED]} unchanged**",
        "",
    ]

    regs = regressions(changes)
    if regs:
        lines += [
            "## Regressions",
            "",
            "| Project | Score | Grade | What dropped | Scanned commit |",
            "|---|---:|:--:|---|---|",
        ]
        for c in regs:
            sha = (c.get("scanned_sha") or "")[:10] or "—"
            grade = (
                f"{c['grade_from']}→{c['grade_to']}"
                if c["grade_changed"]
                else c["grade_to"]
            )
            lines.append(
                f"| [`{c['project']}`](https://github.com/{c['project']}) "
                f"| {c['score_from']}→{c['score_to']} ({c['score_delta']:+d}) "
                f"| {grade} | {_fmt_dims(c['dimension_deltas']) or '—'} | `{sha}` |"
            )
        lines.append("")
    else:
        lines += ["No regressions this run.", ""]

    improvements = [c for c in changes if c["classification"] == IMPROVEMENT]
    if improvements:
        lines += ["## Improvements", ""]
        for c in improvements:
            lines.append(
                f"- `{c['project']}` {c['score_from']}→{c['score_to']} "
                f"({c['score_delta']:+d}): {_fmt_dims(c['dimension_deltas']) or 'rescored'}"
            )
        lines.append("")

    new = [c for c in changes if c["classification"] == NEW]
    if new:
        lines += ["## Newly tracked", ""]
        for c in new:
            lines.append(f"- `{c['project']}` entered at {c['score_to']}/100 ({c['grade_to']})")
        lines.append("")

    lines += [
        "---",
        "",
        "Every score is reproducible: `agent-contracts scan --root <clone>` at the "
        "recorded commit. This report is generated mechanically from "
        "`leaderboard_history.jsonl`.",
        "",
    ]
    return "\n".join(lines)
