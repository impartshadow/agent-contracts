"""Tests for the living-leaderboard history + regression-diff layer."""

from __future__ import annotations

from agent_contracts import history, regression


def _payload(project, score, grade, components):
    return {
        "project": project,
        "score": score,
        "grade": grade,
        "components": [{"name": k, "points": v, "max_points": 100} for k, v in components.items()],
    }


def test_append_and_load_roundtrip(tmp_path):
    path = tmp_path / "hist.jsonl"
    rows = [_payload("o/a", 90, "A", {"tests_and_ci": 20, "secret_safety": 10})]
    run_id = history.append_run(path, rows, run_id="2026-01-01T00:00:00Z", shas={"o/a": "deadbeef"})
    loaded = history.load_history(path)
    assert run_id == "2026-01-01T00:00:00Z"
    assert len(loaded) == 1
    rec = loaded[0]
    assert rec["project"] == "o/a"
    assert rec["score"] == 90
    assert rec["scanned_sha"] == "deadbeef"
    assert rec["components"]["tests_and_ci"] == 20


def test_load_missing_file_is_empty(tmp_path):
    assert history.load_history(tmp_path / "nope.jsonl") == []


def test_previous_run_map_picks_most_recent_prior(tmp_path):
    path = tmp_path / "hist.jsonl"
    history.append_run(path, [_payload("o/a", 80, "B", {"x": 80})], run_id="2026-01-01T00:00:00Z")
    history.append_run(path, [_payload("o/a", 85, "B", {"x": 85})], run_id="2026-02-01T00:00:00Z")
    hist = history.load_history(path)
    prev = history.previous_run_map(hist, "2026-03-01T00:00:00Z")
    assert prev["o/a"]["score"] == 85  # most recent prior, not the oldest


def test_baseline_run_has_no_previous():
    hist = []
    assert history.previous_run_map(hist, "2026-01-01T00:00:00Z") == {}


def _rec(project, score, grade, components, sha="sha"):
    return {
        "project": project,
        "score": score,
        "grade": grade,
        "components": components,
        "scanned_sha": sha,
    }


def test_diff_detects_score_regression_and_grade_drop():
    prev = {"o/a": _rec("o/a", 95, "A", {"secret_safety": 15, "tests_and_ci": 20})}
    curr = {"o/a": _rec("o/a", 80, "B", {"secret_safety": 0, "tests_and_ci": 20})}
    changes = regression.diff_runs(prev, curr)
    assert len(changes) == 1
    c = changes[0]
    assert c["classification"] == regression.REGRESSION
    assert c["severity"] == regression.CRITICAL  # grade dropped + >=10 point fall
    assert c["score_delta"] == -15
    assert c["grade_changed"] is True
    dims = {d["name"]: d["delta"] for d in c["dimension_deltas"]}
    assert dims["secret_safety"] == -15


def test_diff_single_dimension_drop_is_warn_regression():
    prev = {"o/a": _rec("o/a", 95, "A", {"secret_safety": 15, "resilience": 10})}
    curr = {"o/a": _rec("o/a", 90, "A", {"secret_safety": 10, "resilience": 10})}
    c = regression.diff_runs(prev, curr)[0]
    assert c["classification"] == regression.REGRESSION
    assert c["severity"] == regression.WARN  # small fall, same grade


def test_diff_improvement_and_new_and_unchanged():
    prev = {
        "o/improve": _rec("o/improve", 80, "B", {"x": 80}),
        "o/same": _rec("o/same", 90, "A", {"x": 90}),
    }
    curr = {
        "o/improve": _rec("o/improve", 88, "B", {"x": 88}),
        "o/same": _rec("o/same", 90, "A", {"x": 90}),
        "o/new": _rec("o/new", 70, "C", {"x": 70}),
    }
    by = {c["project"]: c for c in regression.diff_runs(prev, curr)}
    assert by["o/improve"]["classification"] == regression.IMPROVEMENT
    assert by["o/same"]["classification"] == regression.UNCHANGED
    assert by["o/new"]["classification"] == regression.NEW


def test_regressions_sort_first_worst_drop_leads():
    prev = {
        "o/small": _rec("o/small", 95, "A", {"x": 95}),
        "o/big": _rec("o/big", 95, "A", {"x": 95}),
    }
    curr = {
        "o/small": _rec("o/small", 92, "A", {"x": 92}),
        "o/big": _rec("o/big", 70, "C", {"x": 70}),
    }
    changes = regression.diff_runs(prev, curr)
    assert changes[0]["project"] == "o/big"  # critical regression leads


def test_trend_cell_labels():
    prev = {"o/a": _rec("o/a", 95, "A", {"x": 95})}
    curr_down = {"o/a": _rec("o/a", 90, "A", {"x": 90})}
    down = regression.diff_runs(prev, curr_down)[0]
    assert regression.trend_cell(down) == "▼ -5"

    curr_up = {"o/a": _rec("o/a", 98, "A", {"x": 98})}
    up = regression.diff_runs(prev, curr_up)[0]
    assert regression.trend_cell(up) == "▲ +3"

    new = regression.diff_project(None, _rec("o/x", 70, "C", {"x": 70}))
    assert regression.trend_cell(new) == "new"
    assert regression.trend_cell(None) == "–"


def test_render_markdown_has_regression_table():
    prev = {"o/a": _rec("o/a", 95, "A", {"secret_safety": 15})}
    curr = {"o/a": _rec("o/a", 80, "B", {"secret_safety": 0})}
    changes = regression.diff_runs(prev, curr)
    md = regression.render_regressions_markdown(
        changes, run_id="2026-02-01T00:00:00Z", prev_run_id="2026-01-01T00:00:00Z"
    )
    assert "## Regressions" in md
    assert "o/a" in md
    assert "secret_safety 15→0" in md
    assert "1 regressions" in md


def test_render_markdown_baseline_no_prior():
    new = regression.diff_project(None, _rec("o/a", 90, "A", {"x": 90}))
    md = regression.render_regressions_markdown(
        [new], run_id="2026-01-01T00:00:00Z", prev_run_id=None
    )
    assert "baseline" in md.lower()
    assert "No regressions this run." in md
