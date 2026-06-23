#!/usr/bin/env python3
"""Clone well-known public agent repos, scan them, record history, diff, publish.

The leaderboard is only credible if it contains real, recognizable agent
projects scored by the same mechanical scanner anyone can run — and it is only
*alive* if every scan is recorded and the next scan is diffed against the last.
This script:

1. shallow-clones a curated set of public agent repos into a temp dir,
2. runs ``scan_repository`` on each, capturing the exact scored commit SHA,
3. appends the run to ``leaderboard_history.jsonl`` (durable provenance),
4. diffs against the previous recorded run and writes a change report,
5. regenerates LEADERBOARD.md (with a trend column) and the published HTML
   leaderboard (trend column + a data-driven "what changed" banner).

Usage: python scripts/seed_leaderboard.py [--workdir DIR] [--keep]
                                          [--no-track] [--no-docs]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent_contracts.scan import scan_repository  # noqa: E402
from agent_contracts import history as history_mod  # noqa: E402
from agent_contracts import regression as regression_mod  # noqa: E402

HISTORY_PATH = REPO_ROOT / history_mod.DEFAULT_HISTORY_FILENAME
LEADERBOARD_MD = REPO_ROOT / "LEADERBOARD.md"
REGRESSIONS_MD = REPO_ROOT / "REGRESSIONS.md"
REGRESSIONS_JSON = REPO_ROOT / "regressions.json"
LEADERBOARD_HTML = REPO_ROOT / "docs" / "leaderboard" / "index.html"

# Markers in the published HTML that this script owns and regenerates.
ROWS_START = "<!-- LB:ROWS:START -->"
ROWS_END = "<!-- LB:ROWS:END -->"
FINDING_START = "<!-- LB:FINDING:START -->"
FINDING_END = "<!-- LB:FINDING:END -->"

# Curated, recognizable, public agent/agent-framework repos.
SEED_REPOS = [
    "Significant-Gravitas/AutoGPT",
    "yoheinakajima/babyagi",
    "openai/swarm",
    "crewAIInc/crewAI",
    "langchain-ai/langgraph",
    "microsoft/autogen",
    "All-Hands-AI/OpenHands",
    "geekan/MetaGPT",
    "langchain-ai/langchain",
    "run-llama/llama_index",
    "microsoft/semantic-kernel",
    "princeton-nlp/SWE-agent",
    "camel-ai/camel",
    "TransformerOptimus/SuperAGI",
    "assafelovic/gpt-researcher",
    "stanfordnlp/dspy",
    "pydantic/pydantic-ai",
    "huggingface/smolagents",
    "openai/openai-agents-python",
    "google/adk-python",
    "letta-ai/letta",
    "mem0ai/mem0",
    "OpenBMB/ChatDev",
    "reworkd/AgentGPT",
    "agno-agi/agno",
    "Aider-AI/aider",
    "microsoft/JARVIS",
]


def head_sha(repo_dir: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


def clone(repo: str, dest: Path) -> tuple[Path | None, str | None]:
    url = f"https://github.com/{repo}.git"
    target = dest / repo.replace("/", "__")
    if target.exists():
        return target, head_sha(target)
    print(f"cloning {repo} ...", flush=True)
    # --depth 1 is safe: scan_repository reads only the working tree at HEAD and
    # skips .git entirely. If secret_safety ever scans git history for leaked keys,
    # drop --depth here or those commits won't be visible.
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", url, str(target)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        print(f"  FAIL {repo}: {result.stderr.strip()[:200]}", flush=True)
        return None, None
    return target, head_sha(target)


def _trend_label(change: dict | None) -> str:
    return regression_mod.trend_cell(change)


def render_leaderboard(rows: list[dict], changes_by_project: dict[str, dict]) -> str:
    rows = sorted(rows, key=lambda r: r["score"], reverse=True)
    lines = [
        "# Shadow Agent Governance Index",
        "",
        "A public, mechanical scorecard for autonomous-agent repositories.",
        "Every score is the output of `agent-contracts scan` against a clean clone —",
        "no vibes, no testimonials. The scanner reads observable governance *surface*",
        "(tests/CI, tool gating, secret hygiene, dependency pinning, eval harness,",
        "observability, resilience). It does not claim the agent is safe at runtime;",
        "it measures whether the guardrails a reliable agent needs are present.",
        "",
        "The **Trend** column is the movement since the previous scan — this index is",
        "re-run on a schedule, so a dropped guardrail shows up here as a regression.",
        "",
        "Scores are intentionally harsh. A missing dimension earns zero — there is no",
        "credit for a story about what the agent probably does.",
        "",
        "| Rank | Project | Score | Grade | Trend | Strongest | Weakest |",
        "|---:|---|---:|:--:|:--:|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        comps = r["components"]
        strongest = max(comps, key=lambda c: c["points"] / c["max_points"])
        weakest = min(comps, key=lambda c: c["points"] / c["max_points"])
        weakest_label = "—" if weakest["points"] == weakest["max_points"] else weakest["name"]
        trend = _trend_label(changes_by_project.get(r["project"]))
        lines.append(
            f"| {i} | [`{r['project']}`](https://github.com/{r['project']}) "
            f"| {r['score']}/100 | {r['grade']} | {trend} "
            f"| {strongest['name']} | {weakest_label} |"
        )
    lines.extend(
        [
            "",
            "## Reproduce any score",
            "",
            "```bash",
            'pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"',
            "git clone --depth 1 https://github.com/<owner>/<repo>.git",
            "agent-contracts scan --root <repo> --json",
            "```",
            "",
            "## Submit your agent",
            "",
            "Open an issue with your repo URL, or run `agent-contracts scan --root . "
            "--output-markdown AGENT_GOVERNANCE_SCORE.md` and open a PR adding the row.",
            "Self-scores are accepted only when reproducible from a clean clone.",
            "",
            "## Dimensions (100 points)",
            "",
            "| Dimension | Max | What it checks |",
            "|---|---:|---|",
            "| tests_and_ci | 20 | a test suite plus CI that runs it |",
            "| tool_governance | 20 | permission/allowlist/approval/human-in-loop gating |",
            "| secret_safety | 15 | secrets git-ignored, no obvious hardcoded keys |",
            "| dependency_pinning | 10 | a lockfile or pinned dependency manifest |",
            "| eval_harness | 15 | an eval / benchmark / labeled-corpus surface |",
            "| observability | 10 | logging / audit / tracing |",
            "| resilience | 10 | retry / backoff / fallback / escalation |",
        ]
    )
    return "\n".join(lines) + "\n"


def _grade_class(grade: str) -> str:
    return {"A": "A", "B": "B", "C": "C", "D": "D", "F": "D"}.get(grade, "D")


def _trend_html(change: dict | None) -> str:
    label = _trend_label(change)
    if label.startswith("▼"):
        cls, color = "down", "var(--block)"
    elif label.startswith("▲"):
        cls, color = "up", "var(--pass)"
    elif label == "new":
        cls, color = "new", "var(--accent)"
    else:
        cls, color = "flat", "var(--muted)"
    return f'<span class="trend {cls}" style="color:{color}">{label}</span>'


def render_html_rows(rows: list[dict], changes_by_project: dict[str, dict]) -> str:
    rows = sorted(rows, key=lambda r: r["score"], reverse=True)
    out = []
    for i, r in enumerate(rows, 1):
        comps = r["components"]
        strongest = max(comps, key=lambda c: c["points"] / c["max_points"])
        weakest = min(comps, key=lambda c: c["points"] / c["max_points"])
        weakest_label = "—" if weakest["points"] == weakest["max_points"] else weakest["name"]
        anchor = r["project"].split("/")[-1].lower().replace("_", "-")
        trend = _trend_html(changes_by_project.get(r["project"]))
        out.append(
            f'    <tr id="{anchor}"><td class="rank">{i}</td>'
            f'<td class="proj"><a href="https://github.com/{r["project"]}">{r["project"]}</a></td>'
            f'<td class="score">{r["score"]}</td>'
            f'<td><span class="grade {_grade_class(r["grade"])}">{r["grade"]}</span></td>'
            f'<td class="trend-cell">{trend}</td>'
            f'<td>{strongest["name"]}</td>'
            f'<td class="weak">{weakest_label}</td></tr>'
        )
    return "\n".join(out)


def render_finding_html(
    changes: list[dict], rows: list[dict], prev_run_id: str | None
) -> str:
    counts = regression_mod.summarize(changes)
    if prev_run_id is None or (counts[regression_mod.REGRESSION] == 0 and counts[regression_mod.IMPROVEMENT] == 0):
        # Baseline run, or no movement: fall back to the structural finding.
        weakest_counts: dict[str, int] = {}
        for r in rows:
            comps = r["components"]
            weakest = min(comps, key=lambda c: c["points"] / c["max_points"])
            if weakest["points"] != weakest["max_points"]:
                weakest_counts[weakest["name"]] = weakest_counts.get(weakest["name"], 0) + 1
        if weakest_counts:
            worst = max(weakest_counts, key=weakest_counts.get)
            n = weakest_counts[worst]
            label = worst.replace("_", " ")
            return (
                f'  <b>The finding:</b> the single most common weakest dimension is '
                f'<b>{label}</b> — {n} of {len(rows)} frameworks score it lowest. '
                f'The gap between "has a test suite" and "won\'t leak a key" is where '
                f'agent reliability actually breaks.'
            )
        return "  <b>Baseline scan recorded.</b> Future scans will diff against it."

    regs = regression_mod.regressions(changes)
    if regs:
        top = regs[0]
        worst = (
            f'<a href="https://github.com/{top["project"]}">{top["project"]}</a> '
            f'{top["score_from"]}→{top["score_to"]} ({top["score_delta"]:+d})'
        )
        return (
            f'  <b>What changed:</b> {counts[regression_mod.REGRESSION]} regression(s), '
            f'{counts[regression_mod.IMPROVEMENT]} improvement(s) since the last scan. '
            f'Biggest drop: {worst}. Every delta is reproducible at the recorded commit.'
        )
    return (
        f'  <b>What changed:</b> no regressions this scan — '
        f'{counts[regression_mod.IMPROVEMENT]} framework(s) improved their governance surface.'
    )


def _replace_between(text: str, start: str, end: str, payload: str) -> str:
    i = text.find(start)
    j = text.find(end)
    if i == -1 or j == -1 or j < i:
        return text  # markers absent — leave HTML untouched rather than corrupt it
    return text[: i + len(start)] + "\n" + payload + "\n" + text[j:]


def update_html(rows: list[dict], changes: list[dict], changes_by_project: dict, prev_run_id):
    if not LEADERBOARD_HTML.exists():
        print(f"  (skip HTML: {LEADERBOARD_HTML} not found)", flush=True)
        return
    html = LEADERBOARD_HTML.read_text(encoding="utf-8")
    if ROWS_START not in html:
        print("  (skip HTML: markers not present — run once after adding markers)", flush=True)
        return
    html = _replace_between(html, ROWS_START, ROWS_END, render_html_rows(rows, changes_by_project))
    html = _replace_between(
        html, FINDING_START, FINDING_END, render_finding_html(changes, rows, prev_run_id)
    )
    LEADERBOARD_HTML.write_text(html, encoding="utf-8")
    print(f"  updated {LEADERBOARD_HTML}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--no-track", action="store_true", help="skip writing history/diff")
    parser.add_argument("--no-docs", action="store_true", help="skip updating published HTML")
    args = parser.parse_args()

    workdir = Path(args.workdir) if args.workdir else Path(tempfile.mkdtemp(prefix="acscan_"))
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"workdir: {workdir}", flush=True)

    rows: list[dict] = []
    shas: dict[str, str | None] = {}
    for repo in SEED_REPOS:
        path, sha = clone(repo, workdir)
        if path is None:
            continue
        try:
            payload = scan_repository(path)
            payload["project"] = repo
            rows.append(payload)
            shas[repo] = sha
            print(f"  {repo}: {payload['score']}/100 ({payload['grade']}) @ {(sha or '?')[:10]}", flush=True)
        finally:
            if not args.keep:
                shutil.rmtree(path, ignore_errors=True)

    if not rows:
        print("no repos scored", file=sys.stderr)
        return 1

    changes: list[dict] = []
    changes_by_project: dict[str, dict] = {}
    prev_run_id = None

    if not args.no_track:
        hist = history_mod.load_history(HISTORY_PATH)
        run_id = history_mod.utc_now_iso()
        prior_ids = history_mod.run_ids(hist)
        prev_run_id = prior_ids[-1] if prior_ids else None
        prev_map = history_mod.previous_run_map(hist, run_id) if prev_run_id else {}

        history_mod.append_run(HISTORY_PATH, rows, run_id=run_id, shas=shas)

        curr_map = {
            r["project"]: history_mod.record_from_payload(
                r, run_id=run_id, scanned_at=run_id, scanned_sha=shas.get(r["project"])
            )
            for r in rows
        }
        changes = regression_mod.diff_runs(prev_map, curr_map)
        changes_by_project = {c["project"]: c for c in changes}

        REGRESSIONS_MD.write_text(
            regression_mod.render_regressions_markdown(
                changes, run_id=run_id, prev_run_id=prev_run_id
            ),
            encoding="utf-8",
        )
        REGRESSIONS_JSON.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "prev_run_id": prev_run_id,
                    "summary": regression_mod.summarize(changes),
                    "changes": changes,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        regs = regression_mod.regressions(changes)
        print(
            f"  history: run {run_id} recorded; "
            f"{len(regs)} regression(s) vs {prev_run_id or 'baseline'}",
            flush=True,
        )

    LEADERBOARD_MD.write_text(render_leaderboard(rows, changes_by_project), encoding="utf-8")
    print(f"wrote {LEADERBOARD_MD} with {len(rows)} entries", flush=True)

    if not args.no_docs:
        update_html(rows, changes, changes_by_project, prev_run_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
