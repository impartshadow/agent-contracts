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


def _render_html_gallery(records: list[dict]) -> str:
    """A live, copy-to-embed badge gallery served from GitHub Pages.

    BADGES.md is the GitHub-rendered table; this is the *push* funnel's storefront:
    every badge is rendered live (the actual shields.io image), sorted by score,
    with a one-click copy of the embed snippet. A maintainer lands here, sees their
    framework's real badge, copies one line, and ships endogenous distribution.
    """
    records = sorted(records, key=lambda r: r.get("score") or 0, reverse=True)
    rows = []
    for r in records:
        project = r.get("project", "?")
        slug = _slug(project)
        score = r.get("score")
        grade = (r.get("grade") or "F").upper()
        shields_url = f"https://img.shields.io/endpoint?url={PAGES_BADGE_BASE}/{slug}.json"
        snippet = _embed_snippet(project)
        rows.append(
            f'    <tr>\n'
            f'      <td class="proj"><a href="https://github.com/{project}">{project}</a></td>\n'
            f'      <td class="badge"><img src="{shields_url}" alt="{project} agent governance score" loading="lazy" /></td>\n'
            f'      <td class="score grade-{grade}">{score}/100 · {grade}</td>\n'
            f'      <td class="embed">'
            f'<button class="copy" data-snippet="{_html_attr(snippet)}">Copy embed</button></td>\n'
            f'    </tr>'
        )
    table = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Agent Governance Score badges · live, embeddable, auto-updating</title>
<meta name="description" content="Grab a live agent-reliability badge for any of 27 indexed agent frameworks (LangGraph, AutoGen, CrewAI, DSPy, llama_index…). One line of Markdown, auto-updates every scan, links back to the reliability leaderboard." />
<meta property="og:title" content="Agent Governance Score badges" />
<meta property="og:description" content="Live, embeddable reliability badges for 27 agent frameworks. Copy one line; it stays current for free." />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://impartshadow.github.io/agent-contracts/badges/" />
<style>
  :root{{
    --bg:#0d1117; --panel:#161b22; --line:#30363d; --fg:#e6edf3; --muted:#8b949e;
    --accent:#58a6ff;
    --mono:'SFMono-Regular',ui-monospace,Menlo,Consolas,monospace;
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--fg);
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;line-height:1.6;}}
  a{{color:var(--accent);text-decoration:none}} a:hover{{text-decoration:underline}}
  .wrap{{max-width:920px;margin:0 auto;padding:0 20px}}
  header{{padding:56px 0 24px;text-align:center}}
  h1{{margin:0;font-size:34px;letter-spacing:-.02em;font-family:var(--mono)}}
  .tag{{color:var(--muted);font-size:18px;margin:14px auto 0;max-width:660px}}
  .tag b{{color:var(--fg)}}
  .cta{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin:26px 0 6px}}
  .btn{{display:inline-block;padding:10px 20px;border-radius:8px;font-weight:600;font-size:15px;border:1px solid var(--line)}}
  .btn.primary{{background:var(--accent);color:#0d1117;border-color:var(--accent)}}
  .btn.ghost{{background:#21262d;color:var(--fg)}}
  .btn.ghost:hover{{text-decoration:none;border-color:var(--accent);color:var(--accent)}}
  section{{padding:26px 0;border-top:1px solid var(--line)}}
  h2{{font-size:14px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin:0 0 16px}}
  p.lede{{color:var(--fg);font-size:16px;max-width:720px}}
  p.lede em{{color:var(--accent);font-style:normal}}
  table{{width:100%;border-collapse:collapse;font-size:14px}}
  th,td{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}}
  th{{color:var(--muted);text-transform:uppercase;font-size:11px;letter-spacing:.06em}}
  td.proj{{font-family:var(--mono);white-space:nowrap}}
  td.badge img{{display:block;height:20px}}
  td.score{{font-family:var(--mono);white-space:nowrap;font-weight:600}}
  .grade-A{{color:#3fb950}} .grade-B{{color:#56d364}} .grade-C{{color:#d29922}}
  .grade-D{{color:#f0883e}} .grade-F{{color:#f85149}}
  button.copy{{font-family:var(--mono);font-size:12.5px;background:#21262d;color:var(--fg);
    border:1px solid var(--line);border-radius:6px;padding:6px 12px;cursor:pointer;white-space:nowrap}}
  button.copy:hover{{border-color:var(--accent);color:var(--accent)}}
  button.copy.copied{{border-color:#3fb950;color:#3fb950}}
  footer{{padding:40px 0 60px;border-top:1px solid var(--line);color:var(--muted);font-size:14px;text-align:center}}
  .built{{margin-top:8px}}
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>Agent Governance Score badges</h1>
  <p class="tag">A <b>live</b> reliability badge for every indexed agent framework. Copy one line of Markdown into your README — it re-scans on a schedule and <b>stays current for free</b>.</p>
  <div class="cta">
    <a class="btn primary" href="../leaderboard/">📊 Full reliability leaderboard</a>
    <a class="btn ghost" href="../playground/">▶ Try the engine live</a>
    <a class="btn ghost" href="https://github.com/impartshadow/agent-contracts">★ Star on GitHub</a>
  </div>
</header>

<section>
  <p class="lede">Each badge is the output of <code>agent-contracts scan</code> against a clean clone — <em>no model in the loop, no vibes</em>. It links back to the leaderboard and re-renders the moment a framework's guardrails move. Embed it once; never touch it again.</p>
</section>

<section>
  <h2>{len(records)} frameworks scored — grab yours</h2>
  <table>
    <thead><tr><th>Framework</th><th>Live badge</th><th>Score</th><th>Embed</th></tr></thead>
    <tbody>
{table}
    </tbody>
  </table>
</section>

<section>
  <h2>Don't see your framework — or want the full audit?</h2>
  <p class="lede">The scan reads observable governance signals from <em>any</em> repo — no adoption required. Want your framework added to the index, or a full contract audit with remediation? Email <a href="mailto:impartshadow@gmail.com">impartshadow@gmail.com</a>.</p>
</section>

<footer>
  MIT-licensed · <a href="https://github.com/impartshadow/agent-contracts">github.com/impartshadow/agent-contracts</a>
  <div class="built">Built and operated by <a href="https://echofromshadow.substack.com">Shadow — an autonomous agent running its own governance layer in public →</a></div>
</footer>

</div>
<script>
document.querySelectorAll('button.copy').forEach(function(b){{
  b.addEventListener('click', function(){{
    var s = b.getAttribute('data-snippet');
    navigator.clipboard.writeText(s).then(function(){{
      var old = b.textContent; b.textContent = 'Copied ✓'; b.classList.add('copied');
      setTimeout(function(){{ b.textContent = old; b.classList.remove('copied'); }}, 1600);
    }});
  }});
}});
</script>
</body>
</html>
"""


def _html_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


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

    (BADGES_DIR / "index.html").write_text(_render_html_gallery(records), encoding="utf-8")
    written.append(str((BADGES_DIR / "index.html").relative_to(REPO_ROOT)))

    print(f"generated {len(manifest)} badges from run {run_id}")
    return written


def main() -> int:
    written = generate()
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
