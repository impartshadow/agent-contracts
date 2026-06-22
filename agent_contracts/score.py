"""Repository reliability scoring for agent-contracts adoption."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union

from .doctor import run_doctor
from .eval import evaluate_records
from .policy import load_policy
from .replay import load_jsonl, replay_file


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _badge_color(score: int) -> str:
    if score >= 90:
        return "brightgreen"
    if score >= 80:
        return "green"
    if score >= 70:
        return "yellowgreen"
    if score >= 60:
        return "yellow"
    return "red"


def _badge_url(score: int) -> str:
    return (
        "https://img.shields.io/badge/"
        f"agent%20reliability-{score}%2F100-{_badge_color(score)}"
    )


def badge_endpoint(score: int) -> dict[str, Any]:
    """Return a Shields endpoint JSON payload."""

    return {
        "schemaVersion": 1,
        "label": "agent reliability",
        "message": f"{score}/100",
        "color": _badge_color(score),
    }


def _component(name: str, points: int, max_points: int, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "points": max(0, min(points, max_points)),
        "max_points": max_points,
        "details": details,
    }


def _doctor_component(doctor: dict[str, Any]) -> dict[str, Any]:
    required_total = int(doctor.get("required_total") or 0)
    required_passed = int(doctor.get("required_passed") or 0)
    points = round(40 * (required_passed / required_total)) if required_total else 0
    return _component(
        "adoption_wiring",
        points,
        40,
        {
            "required_passed": required_passed,
            "required_total": required_total,
            "passed": bool(doctor.get("passed")),
        },
    )


def _matrix_component(doctor: dict[str, Any]) -> dict[str, Any]:
    matrix = next((c for c in doctor.get("checks", []) if c.get("name") == "built-in-matrix"), None)
    points = 20 if matrix and matrix.get("passed") else 0
    return _component(
        "built_in_contract_matrix",
        points,
        20,
        {"passed": bool(matrix and matrix.get("passed"))},
    )


def _eval_component(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return _component(
            "labeled_eval_corpus",
            0,
            25,
            {"configured": False, "message": "no eval corpus supplied"},
        )
    accuracy = float(payload.get("accuracy") or 0.0)
    recall = float(payload.get("recall") or 0.0)
    precision = float(payload.get("precision") or 0.0)
    points = round(25 * ((accuracy * 0.4) + (recall * 0.4) + (precision * 0.2)))
    return _component(
        "labeled_eval_corpus",
        points,
        25,
        {
            "configured": True,
            "records": payload.get("records", 0),
            "labeled_records": payload.get("labeled_records", 0),
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "passed": bool(payload.get("passed")),
        },
    )


def _replay_component(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    if rows is None:
        return _component(
            "incident_replay",
            0,
            15,
            {"configured": False, "message": "no replay log supplied"},
        )
    if not rows:
        return _component(
            "incident_replay",
            0,
            15,
            {"configured": True, "records": 0, "message": "replay file was empty"},
        )
    blocked = sum(1 for row in rows if row.get("blocked"))
    violations = sum(len(row.get("violations") or []) for row in rows)
    coverage = (blocked + violations) / (len(rows) * 2)
    points = round(15 * min(coverage, 1.0))
    return _component(
        "incident_replay",
        points,
        15,
        {
            "configured": True,
            "records": len(rows),
            "blocked_records": blocked,
            "violation_count": violations,
        },
    )


def score_repository(
    root: Union[str, Path] = ".",
    *,
    policy_path: Union[str, Path, None] = None,
    eval_path: Union[str, Path, None] = None,
    replay_path: Union[str, Path, None] = None,
) -> dict[str, Any]:
    """Score a repository's agent governance adoption on a 0-100 scale.

    The score is deliberately mechanical:

    - 40 points: required adoption wiring detected by ``doctor``.
    - 20 points: built-in contract matrix passes.
    - 25 points: optional labeled eval corpus quality.
    - 15 points: optional incident replay coverage.
    """

    base = Path(root)
    doctor = run_doctor(base, policy_path=policy_path, eval_path=eval_path)

    evaluation = None
    if eval_path:
        policy = Path(policy_path) if policy_path else base / "agent-contracts.yml"
        if not policy.is_absolute():
            policy = base / policy
        corpus = Path(eval_path)
        if not corpus.is_absolute():
            corpus = base / corpus
        if policy.exists() and corpus.exists():
            evaluation = evaluate_records(load_jsonl(corpus), load_policy(policy))

    replay_rows = None
    if replay_path:
        policy = Path(policy_path) if policy_path else base / "agent-contracts.yml"
        if not policy.is_absolute():
            policy = base / policy
        incident_log = Path(replay_path)
        if not incident_log.is_absolute():
            incident_log = base / incident_log
        if policy.exists() and incident_log.exists():
            replay_rows = replay_file(incident_log, load_policy(policy))

    components = [
        _doctor_component(doctor),
        _matrix_component(doctor),
        _eval_component(evaluation),
        _replay_component(replay_rows),
    ]
    score = sum(component["points"] for component in components)
    return {
        "score": score,
        "grade": _grade(score),
        "passed": score >= 70,
        "badge_url": _badge_url(score),
        "badge_endpoint": badge_endpoint(score),
        "badge_markdown": f"[![Agent reliability: {score}/100]({_badge_url(score)})](https://impartshadow.github.io/agent-contracts/leaderboard/)",
        "components": components,
        "doctor": doctor,
    }


def render_scorecard_markdown(payload: dict[str, Any]) -> str:
    """Render a commit-ready scorecard for public repos."""

    rows = [
        f"| {component['name']} | {component['points']} / {component['max_points']} |"
        for component in payload["components"]
    ]
    return "\n".join(
        [
            "# Agent Reliability Score",
            "",
            f"**Score: {payload['score']}/100 (grade {payload['grade']})**",
            "",
            payload["badge_markdown"],
            "",
            "| Component | Points |",
            "|---|---:|",
            *rows,
            "",
            "This score is mechanical, not a testimonial. It weights adoption wiring,",
            "the built-in contract matrix, labeled eval coverage, and incident replay.",
            "Missing eval or replay data earns zero for that component.",
            "",
            "Reproduce:",
            "",
            "```bash",
            "agent-contracts score --root . --eval examples/eval_corpus.jsonl --replay examples/actions.jsonl --json",
            "```",
        ]
    )
