#!/usr/bin/env python3
"""Generate one SEO-discoverable governance report card per indexed framework.

The leaderboard is a single page; the long-tail search is per-framework
("is LangGraph production-ready", "AutoGPT security audit", "CrewAI reliability
score"). This script turns each row of the index into its own static page so
that high-intent query has a real, reproducible answer to land on — every page
links the exact scanned commit SHA so any score is reproducible from a clean
clone.

Runs two ways:
  * standalone   — reads the latest run from leaderboard_history.jsonl, so it can
                   regenerate the pages without re-cloning 27 repos.
  * from a scan  — seed_leaderboard.py calls generate(rows=..., shas=...) right
                   after a fresh scan, so the pages compound on every run.

Usage: python scripts/gen_framework_pages.py
"""

from __future__ import annotations

import html as _html
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent_contracts import history as history_mod  # noqa: E402

HISTORY_PATH = REPO_ROOT / history_mod.DEFAULT_HISTORY_FILENAME
OUT_DIR = REPO_ROOT / "docs" / "frameworks"
SITE = "https://impartshadow.github.io/agent-contracts"
SUBSTACK = "https://echofromshadow.substack.com"
SUBSCRIBE = "https://echofromshadow.substack.com/subscribe"
ESSAY = "https://echofromshadow.substack.com/p/i-built-a-scorecard-for-agent-frameworks"

# Fixed point budget per dimension (mirrors LEADERBOARD.md "Dimensions" table).
DIMENSIONS = [
    ("tests_and_ci", 20, "a test suite plus CI that runs it"),
    ("tool_governance", 20, "permission / allowlist / approval / human-in-loop gating on tool calls"),
    ("secret_safety", 15, "secrets git-ignored, no obvious hardcoded keys"),
    ("eval_harness", 15, "an eval / benchmark / labeled-corpus surface"),
    ("dependency_pinning", 10, "a lockfile or pinned dependency manifest"),
    ("observability", 10, "logging / audit / tracing"),
    ("resilience", 10, "retry / backoff / fallback / escalation"),
]
DIM_MAX = {name: mx for name, mx, _ in DIMENSIONS}
DIM_WHAT = {name: what for name, _, what in DIMENSIONS}

STYLE = """
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--muted:#8b949e;
--accent:#58a6ff;--block:#f85149;--warn:#d29922;--pass:#3fb950;
--mono:'SFMono-Regular',ui-monospace,Menlo,Consolas,monospace;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;line-height:1.6;}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:760px;margin:0 auto;padding:0 20px}
.crumb{font-family:var(--mono);font-size:13px;color:var(--muted);padding:24px 0 0}
header{padding:18px 0 8px}
h1{margin:0;font-size:28px;letter-spacing:-.02em}
h1 .repo{font-family:var(--mono);font-size:24px}
.tag{color:var(--muted);font-size:17px;margin:12px 0 0}
.scorebox{display:flex;align-items:baseline;gap:14px;margin:22px 0 4px}
.bigscore{font-family:var(--mono);font-size:46px;font-weight:700}
.grade{font-family:var(--mono);font-weight:700;padding:3px 12px;border-radius:6px;font-size:20px}
.A{color:var(--pass);background:rgba(63,185,80,.12)}
.B{color:var(--accent);background:rgba(88,166,255,.12)}
.C{color:var(--warn);background:rgba(210,153,34,.12)}
.D{color:var(--block);background:rgba(248,81,73,.12)}
.trend{font-family:var(--mono);font-size:14px;color:var(--muted)}
.finding{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--warn);
border-radius:10px;padding:16px 18px;margin:20px 0;font-size:15.5px}
.finding b{color:var(--warn)}
section{padding:26px 0;border-top:1px solid var(--line)}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin:0 0 16px}
.dim{margin:0 0 14px}
.dim .row{display:flex;justify-content:space-between;font-size:14px;margin:0 0 5px}
.dim .row .what{color:var(--muted);font-size:12.5px}
.dim .pts{font-family:var(--mono)}
.bar{height:7px;background:#21262d;border-radius:4px;overflow:hidden}
.bar > i{display:block;height:100%;border-radius:4px}
.full{background:var(--pass)}.part{background:var(--warn)}.zero{background:var(--block)}
pre{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;overflow-x:auto;
font-family:var(--mono);font-size:13px;line-height:1.55;margin:0}
.cta{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0 4px}
.btn{display:inline-block;padding:10px 20px;border-radius:8px;font-weight:600;font-size:14.5px;border:1px solid var(--line)}
.btn.primary{background:var(--accent);color:#0d1117;border-color:var(--accent)}
.btn.ghost{background:#21262d;color:var(--fg)}
.note{color:var(--muted);font-size:13px;margin-top:14px}
footer{padding:36px 0 56px;border-top:1px solid var(--line);color:var(--muted);font-size:13.5px}
ul.idx{list-style:none;padding:0;margin:0}
ul.idx li{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--line);font-size:14px}
ul.idx .nm{font-family:var(--mono);font-size:13.5px}
"""


def _grade_class(grade: str) -> str:
    return {"A": "A", "B": "B", "C": "C", "D": "D", "F": "D"}.get(grade, "D")


def _slug(project: str) -> str:
    return project.replace("/", "__")


def _bar_class(pts: int, mx: int) -> str:
    if pts >= mx:
        return "full"
    if pts == 0:
        return "zero"
    return "part"


def _trend_text(score: int, prev_score: int | None) -> str:
    if prev_score is None:
        return "first scan on record"
    delta = score - prev_score
    if delta > 0:
        return f"▲ +{delta} since the previous scan"
    if delta < 0:
        return f"▼ {delta} since the previous scan"
    return "no change since the previous scan"


def _render_card(rec: dict, prev_score: int | None) -> str:
    project = rec["project"]
    owner, repo = project.split("/", 1)
    score = rec["score"]
    grade = rec["grade"]
    gcls = _grade_class(grade)
    sha = rec.get("scanned_sha") or ""
    short_sha = sha[:10] if sha else "HEAD"
    comps = rec.get("components", {})

    # weakest scored dimension (lowest ratio that isn't already full)
    ranked = sorted(
        DIM_MAX.keys(),
        key=lambda n: (comps.get(n, 0) / DIM_MAX[n]),
    )
    weakest = next((n for n in ranked if comps.get(n, 0) < DIM_MAX[n]), None)

    dims_html = []
    for name, mx, what in DIMENSIONS:
        pts = comps.get(name, 0)
        pct = round(100 * pts / mx)
        dims_html.append(
            f'<div class="dim"><div class="row"><span>{name}'
            f'<span class="what"> — {_html.escape(what)}</span></span>'
            f'<span class="pts">{pts}/{mx}</span></div>'
            f'<div class="bar"><i class="{_bar_class(pts, mx)}" style="width:{pct}%"></i></div></div>'
        )
    dims_block = "\n".join(dims_html)

    if weakest:
        wmx = DIM_MAX[weakest]
        wpts = comps.get(weakest, 0)
        finding = (
            f'<b>Weakest dimension:</b> {weakest} ({wpts}/{wmx}). '
            f'This measures {_html.escape(DIM_WHAT[weakest])}. A low score here means an '
            f'agent built on {repo} can fail in this dimension without the repo signalling it.'
        )
    else:
        finding = (
            f'<b>Full governance surface.</b> {repo} scores the maximum on every measured '
            f'dimension. Note: a perfect surface score does <i>not</i> mean agents built on it '
            f'tell the truth at runtime — '
            f'<a href="{ESSAY}">that failure has no surface to grep</a>.'
        )

    trend = _trend_text(score, prev_score)
    title = f"Is {repo} production-ready? Agent governance score: {score}/100 ({grade})"
    desc = (
        f"{project} scores {score}/100 (grade {grade}) on the Shadow Agent Governance Index — "
        f"a mechanical, reproducible audit of tests/CI, tool gating, secret hygiene, dependency "
        f"pinning, eval harness, observability and resilience. Reproduced from commit {short_sha}."
    )
    canonical = f"{SITE}/frameworks/{_slug(project)}.html"

    jsonld = (
        '{"@context":"https://schema.org","@type":"Dataset",'
        f'"name":"{_html.escape(project)} agent governance score",'
        f'"description":"{_html.escape(desc)}",'
        f'"url":"{canonical}",'
        '"creator":{"@type":"Organization","name":"Shadow"},'
        '"isBasedOn":"https://github.com/' + project + '",'
        '"license":"https://opensource.org/licenses/MIT"}'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{_html.escape(title)}</title>
<meta name="description" content="{_html.escape(desc)}" />
<link rel="canonical" href="{canonical}" />
<meta property="og:title" content="{_html.escape(title)}" />
<meta property="og:description" content="{_html.escape(desc)}" />
<meta property="og:type" content="article" />
<meta property="og:url" content="{canonical}" />
<meta name="twitter:card" content="summary" />
<script type="application/ld+json">{jsonld}</script>
<style>{STYLE}</style>
</head>
<body>
<div class="wrap">
  <div class="crumb"><a href="{SITE}/leaderboard/">‹ Agent Governance Index</a></div>
  <header>
    <h1>Is <span class="repo">{_html.escape(project)}</span> production-ready?</h1>
    <p class="tag">Mechanical governance score from <b>agent-contracts scan</b> against a clean clone.
    No vibes, no testimonials — reproducible from the exact commit below.</p>
    <div class="scorebox">
      <span class="bigscore">{score}<span style="font-size:22px;color:var(--muted)">/100</span></span>
      <span class="grade {gcls}">{grade}</span>
      <span class="trend">{trend}</span>
    </div>
  </header>

  <div class="finding">{finding}</div>

  <section>
    <h2>Dimension breakdown (100 points)</h2>
    {dims_block}
  </section>

  <section>
    <h2>Reproduce this score</h2>
    <pre>pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"
git clone --depth 1 https://github.com/{project}.git
git -C {repo} checkout {short_sha}
agent-contracts scan --root {repo} --json</pre>
    <p class="note">Scored commit: <code>{sha or 'HEAD at scan time'}</code>. The score is the
    output of a deterministic scanner, not a judgment call — a clean clone reproduces it.</p>
  </section>

  <section>
    <h2>What this score can and can't tell you</h2>
    <p>This index measures observable governance <i>surface</i> — the guardrails a reliable
    agent needs. It does <b>not</b> certify that agents built on {repo} behave correctly at
    runtime. The most expensive agent failure — confidently claiming a task is "done" with
    nothing to back it — has no surface to grep, so no static score (including this one) can
    see it. <a href="{ESSAY}">Here's the proof, on the #1-ranked framework.</a></p>
    <div class="cta">
      <a class="btn primary" href="{SUBSCRIBE}">Get the weekly scan delta — $7/mo</a>
      <a class="btn ghost" href="{SITE}/leaderboard/">See the full index</a>
    </div>
    <p class="note">Every framework is re-scanned on a schedule. The weekly delta — what moved,
    on which commit, and what it means for teams building on it — goes out at
    <a href="{SUBSTACK}">echofromshadow.substack.com</a>.</p>
  </section>

  <footer>
    Shadow Agent Governance Index · <a href="https://github.com/impartshadow/agent-contracts">source on GitHub</a> ·
    scores are mechanical and reproducible · MIT licensed.
  </footer>
</div>
</body>
</html>
"""


def _render_index(records: list[dict]) -> str:
    records = sorted(records, key=lambda r: r["score"], reverse=True)
    rows = []
    for r in records:
        project = r["project"]
        gcls = _grade_class(r["grade"])
        rows.append(
            f'<li><a class="nm" href="{_slug(project)}.html">{_html.escape(project)}</a>'
            f'<span><span class="pts" style="font-family:var(--mono)">{r["score"]}/100</span> '
            f'<span class="grade {gcls}">{r["grade"]}</span></span></li>'
        )
    rows_html = "\n".join(rows)
    desc = (
        "Per-framework agent governance report cards — reproducible reliability scores for "
        "LangGraph, AutoGen, CrewAI, AutoGPT, DSPy, llama_index, OpenHands, aider and 20+ more."
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Agent Framework Governance Report Cards — Shadow Agent Governance Index</title>
<meta name="description" content="{_html.escape(desc)}" />
<link rel="canonical" href="{SITE}/frameworks/" />
<style>{STYLE}</style>
</head>
<body>
<div class="wrap">
  <div class="crumb"><a href="{SITE}/leaderboard/">‹ Agent Governance Index</a></div>
  <header>
    <h1>Framework report cards</h1>
    <p class="tag">One reproducible governance report card per indexed framework. Each links the
    exact scanned commit so any score can be reproduced from a clean clone.</p>
  </header>
  <section>
    <h2>{len(records)} frameworks indexed</h2>
    <ul class="idx">
{rows_html}
    </ul>
  </section>
  <footer>
    Shadow Agent Governance Index · <a href="https://github.com/impartshadow/agent-contracts">source</a> ·
    weekly deltas at <a href="{SUBSTACK}">echofromshadow.substack.com</a>.
  </footer>
</div>
</body>
</html>
"""


def generate(rows: list[dict] | None = None, shas: dict | None = None) -> int:
    """Write one report card per framework + an index. Returns count written.

    When ``rows`` is given (live scan payloads from seed_leaderboard), uses them
    directly. Otherwise reads the latest recorded run from history.
    """
    prev_scores: dict[str, int] = {}
    if rows is not None:
        records = []
        for r in rows:
            comps = r.get("components", {})
            # live scan payload: components is a list of {name,points,max_points}
            if isinstance(comps, list):
                comps = {c["name"]: c["points"] for c in comps}
            records.append(
                {
                    "project": r["project"],
                    "score": r["score"],
                    "grade": r["grade"],
                    "components": comps,
                    "scanned_sha": (shas or {}).get(r["project"]),
                }
            )
    else:
        hist = history_mod.load_history(HISTORY_PATH)
        ids = history_mod.run_ids(hist)
        if not ids:
            print("no runs in history; nothing to generate", file=sys.stderr)
            return 0
        latest = history_mod.run_map(hist, ids[-1])
        records = list(latest.values())
        if len(ids) >= 2:
            prev = history_mod.run_map(hist, ids[-2])
            prev_scores = {p: rec["score"] for p, rec in prev.items()}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for rec in records:
        prev = prev_scores.get(rec["project"])
        path = OUT_DIR / f"{_slug(rec['project'])}.html"
        path.write_text(_render_card(rec, prev), encoding="utf-8")
        written += 1
    (OUT_DIR / "index.html").write_text(_render_index(records), encoding="utf-8")
    print(f"wrote {written} framework report cards + index to {OUT_DIR}", flush=True)
    return written


if __name__ == "__main__":
    raise SystemExit(0 if generate() else 1)
