#!/usr/bin/env python3
"""gen_badges.py — mint a self-updating governance-score badge per indexed framework.

The living index already re-scans 27 frameworks on a schedule and pushes the
refreshed leaderboard. But a leaderboard is a *pull* surface: it only reaches the
ICP when someone visits it. A badge is a *push* surface that the ICP installs for
us. When a maintainer embeds their framework's governance-score badge in a README,
that badge:

  * renders Shadow's score on the maintainer's own repo (third-party proof
    surface, not our page),
  * links back to the leaderboard (a permanent backlink we did not have to place),
  * auto-updates every scan from this same living index (no per-delta push).

Each adopted badge is endogenous distribution that compounds: one embed seeds
every future visitor to that repo, and the score it shows stays live for free.
This is the distribution layer the differentiation thesis calls for — deltas are
only an edge if the ICP sees them, and a badge puts the delta on the ICP's own page.

This reads the latest run from ``leaderboard_history.jsonl`` and emits, into
``docs/badges/``:
  * one shields.io endpoint JSON per framework (``<owner>__<repo>.json``),
  * a manifest (``index.json``) the leaderboard/agent surface can enumerate,
  * ``BADGES.md`` — a copy-paste embed gallery (the adoption funnel).

Served from GitHub Pages, each file is a live shields.io endpoint:
  https://img.shields.io/endpoint?url=https://impartshadow.github.io/agent-contracts/badges/<owner>__<repo>.json

Idempotent; safe to run every scan. Exits 0 unless the history file is missing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_PATH = REPO_ROOT / "leaderboard_history.jsonl"
BADGES_DIR = REPO_ROOT / "docs" / "badges"
LEADERBOARD_URL = "https://impartshadow.github.io/agent-contracts/leaderboard/"
PAGES_BADGE_BASE = "https://impartshadow.github.io/agent-contracts/badges"

# shields.io named colors keyed by grade. Harsh on the low end on purpose —
# a D-grade badge is a nudge to fix, an A-grade badge is social proof.
_GRADE_COLOR = {
    "A": "brightgreen",
    "B": "green",
    "C": "yellow",
    "D": "orange",
    "F": "red",
}


def _slug(project: str) -> str:
    return project.replace("/", "__")


def _latest_run_records() -> list[dict]:
    """Return every per-project record belonging to the most recent run_id."""
    if not HISTORY_PATH.exists():
        return []
    runs: dict[str, list[dict]] = {}
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = rec.get("run_id")
        if rid is None:
            continue
        runs.setdefault(rid, []).append(rec)
    if not runs:
        return []
    latest = max(runs)  # ISO-8601 run_ids sort chronologically as strings
    return runs[latest]


def _endpoint_payload(rec: dict) -> dict:
    score = rec.get("score")
    grade = (rec.get("grade") or "F").upper()
    return {
        "schemaVersion": 1,
        "label": "agent governance",
        "message": f"{score}/100 · {grade}",
        "color": _GRADE_COLOR.get(grade, "lightgrey"),
        "labelColor": "555",
        "namedLogo": "shield",
        "cacheSeconds": 3600,
    }


def _embed_snippet(project: str) -> str:
    slug = _slug(project)
    badge_src = f"https://img.shields.io/endpoint?url={PAGES_BADGE_BASE}/{slug}.json"
    return f"[![Agent Governance Score]({badge_src})]({LEADERBOARD_URL}#{project.split('/')[-1].lower().replace('_', '-')})"


def _render_gallery(records: list[dict]) -> str:
    records = sorted(records, key=lambda r: r.get("score") or 0, reverse=True)
    lines = [
        "# Agent Governance Score badges",
        "",
        "Every indexed framework has a **live** governance-score badge. It is the",
        "output of `agent-contracts scan` against a clean clone, re-scanned on a",
        "schedule — so the badge moves when the framework's guardrails move. Embed",
        "it once; it stays current for free.",
        "",
        "**Maintainers:** drop your row's snippet into your README. The badge links",
        f"back to the [live leaderboard]({LEADERBOARD_URL}) and updates automatically",
        "every scan. No account, no signup — it is a static shields.io endpoint.",
        "",
        "| Project | Score | Embed (Markdown) |",
        "|---|---:|---|",
    ]
    for r in records:
        project = r.get("project", "?")
        score = r.get("score")
        grade = (r.get("grade") or "F").upper()
        snippet = _embed_snippet(project)
        lines.append(
            f"| [`{project}`](https://github.com/{project}) "
            f"| {score}/100 · {grade} | `{snippet}` |"
        )
    lines.extend(
        [
            "",
            "## How it works",
            "",
            "Each badge is a [shields.io endpoint](https://shields.io/badges/endpoint-badge)",
            "served from this repo's GitHub Pages:",
            "",
            "```",
            f"{PAGES_BADGE_BASE}/<owner>__<repo>.json",
            "```",
            "",
            "shields.io fetches that JSON and renders the badge. Because the JSON is",
            "regenerated on every living-index scan, the rendered badge is always the",
            "current score — nothing to re-publish on your side.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def generate() -> list[str]:
    records = _latest_run_records()
    if not records:
        print("no history records found — nothing to badge", file=sys.stderr)
        return []

    BADGES_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    manifest = []

    for rec in records:
        project = rec.get("project")
        if not project:
            continue
        slug = _slug(project)
        path = BADGES_DIR / f"{slug}.json"
        path.write_text(
            json.dumps(_endpoint_payload(rec), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(str(path.relative_to(REPO_ROOT)))
        manifest.append(
            {
                "project": project,
                "slug": slug,
                "score": rec.get("score"),
                "grade": rec.get("grade"),
                "scanned_sha": rec.get("scanned_sha"),
                "scanned_at": rec.get("scanned_at"),
                "badge_endpoint": f"{PAGES_BADGE_BASE}/{slug}.json",
                "shields_url": f"https://img.shields.io/endpoint?url={PAGES_BADGE_BASE}/{slug}.json",
                "embed_markdown": _embed_snippet(project),
            }
        )

    manifest.sort(key=lambda m: m.get("score") or 0, reverse=True)
    run_id = records[0].get("run_id")
    (BADGES_DIR / "index.json").write_text(
        json.dumps(
            {"run_id": run_id, "count": len(manifest), "badges": manifest},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(str((BADGES_DIR / "index.json").relative_to(REPO_ROOT)))

    (REPO_ROOT / "BADGES.md").write_text(_render_gallery(records), encoding="utf-8")
    written.append("BADGES.md")

    print(f"generated {len(manifest)} badges from run {run_id}")
    return written


def main() -> int:
    written = generate()
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
