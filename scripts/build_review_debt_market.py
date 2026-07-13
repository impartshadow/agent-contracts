#!/usr/bin/env python3
"""Compile Review Debt Exchange issues into a public HTML/JSON market."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def _labels(issue: dict) -> set[str]:
    return {item["name"] if isinstance(item, dict) else str(item) for item in issue.get("labels", [])}


def _fields(body: str) -> dict[str, str]:
    chunks = re.split(r"\n###\s+", "\n" + (body or ""))[1:]
    parsed = {}
    for chunk in chunks:
        heading, _, value = chunk.partition("\n")
        parsed[heading.strip()] = value.strip()
    return parsed


def compile_market(issues: list[dict], *, repo: str, generated_at: str | None = None) -> dict:
    checkpoints, proofs = [], []
    for issue in issues:
        labels = _labels(issue)
        title = issue.get("title", "").lower()
        common = {
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["html_url"],
            "author": issue.get("user", {}).get("login", "unknown"),
            "state": issue.get("state", "open"),
            "created_at": issue.get("created_at"),
            "fields": _fields(issue.get("body", "")),
        }
        if "checkpoint" in labels or title.startswith("[checkpoint]"):
            common["market_status"] = "open" if common["state"] == "open" else "closed"
            checkpoints.append(common)
        elif "deletion-proof" in labels or title.startswith("[deletion proof]"):
            common["market_status"] = (
                "accepted" if "operator-accepted" in labels else
                "rejected" if "operator-rejected" in labels else
                "awaiting_operator_verdict"
            )
            proofs.append(common)
    checkpoints.sort(key=lambda item: item["number"], reverse=True)
    proofs.sort(key=lambda item: item["number"], reverse=True)
    return {
        "schema": "review-debt.exchange.v1",
        "repo": repo,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "counts": {
            "open_checkpoints": sum(x["market_status"] == "open" for x in checkpoints),
            "deletion_proofs": len(proofs),
            "accepted_proofs": sum(x["market_status"] == "accepted" for x in proofs),
        },
        "checkpoints": checkpoints,
        "proofs": proofs,
    }


def fetch_issues(repo: str, token: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/issues?state=all&per_page=100"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return [item for item in json.load(response) if "pull_request" not in item]


def render_html(market: dict) -> str:
    def cards(items: list[dict], kind: str) -> str:
        if not items:
            return '<p class="empty">No entries yet. The market is waiting to be falsified.</p>'
        return "\n".join(
            f'<article><span class="status">{html.escape(item["market_status"].replace("_", " "))}</span>'
            f'<h3><a href="{html.escape(item["url"])}">#{item["number"]} {html.escape(item["title"])}</a></h3>'
            f'<p>{kind} · @{html.escape(item["author"])}</p></article>'
            for item in items
        )

    counts = market["counts"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review Debt Exchange</title><meta name="description" content="A public market for deleting recurring human checkpoints from AI workflows.">
<style>
:root{{--ink:#142018;--muted:#536158;--paper:#f5f1e7;--card:#fffdf7;--signal:#d64a2f;--line:#cbc3b2}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}}main{{max-width:960px;margin:auto;padding:64px 24px}}.eyebrow,.status{{text-transform:uppercase;letter-spacing:.1em;font-size:.72rem;color:var(--signal)}}h1{{font:700 clamp(2.6rem,8vw,6rem)/.9 Georgia,serif;max-width:800px;margin:.25em 0}}.lead{{font-size:1.15rem;max-width:720px;color:var(--muted)}}nav{{display:flex;gap:12px;flex-wrap:wrap;margin:30px 0 48px}}a{{color:inherit}}nav a{{background:var(--ink);color:white;text-decoration:none;padding:12px 16px}}nav a.alt{{background:transparent;color:var(--ink);border:1px solid var(--ink)}}.counts{{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--line);margin-bottom:48px}}.counts div{{padding:20px;border-right:1px solid var(--line)}}.counts div:last-child{{border:0}}.counts strong{{display:block;font:700 2rem Georgia,serif}}section{{margin-top:48px}}h2{{font:700 2rem Georgia,serif}}article{{background:var(--card);border:1px solid var(--line);padding:20px;margin:12px 0}}article h3{{margin:.3rem 0}}article p,.empty,footer{{color:var(--muted)}}footer{{margin-top:64px;font-size:.8rem}}@media(max-width:600px){{.counts{{grid-template-columns:1fr}}.counts div{{border-right:0;border-bottom:1px solid var(--line)}}}}
</style></head><body><main>
<p class="eyebrow">A market for the work humans still repeat</p><h1>Delete the checkpoint.</h1>
<p class="lead">Operators list review debt. Agent builders submit runnable deletion proof. The operator decides whether the review can disappear, narrow, or become sampling.</p>
<nav><a href="https://github.com/{market['repo']}/issues/new?template=checkpoint.yml">List review debt</a><a class="alt" href="https://github.com/{market['repo']}/issues/new?template=deletion-proof.yml">Submit deletion proof</a><a class="alt" href="market.json">Machine-readable market</a></nav>
<div class="counts"><div><strong>{counts['open_checkpoints']}</strong>open checkpoints</div><div><strong>{counts['deletion_proofs']}</strong>proof attempts</div><div><strong>{counts['accepted_proofs']}</strong>operator-accepted</div></div>
<section><h2>Review debt</h2>{cards(market['checkpoints'], 'checkpoint')}</section>
<section><h2>Deletion proof</h2>{cards(market['proofs'], 'proof')}</section>
<footer>Generated {html.escape(market['generated_at'])}. Participation, not traffic, is the falsification signal.</footer>
</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "impartshadow/agent-contracts"))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--issues-json", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/review-debt"))
    args = parser.parse_args()
    if args.issues_json:
        issues = json.loads(args.issues_json.read_text(encoding="utf-8"))
    elif args.token:
        issues = fetch_issues(args.repo, args.token)
    else:
        raise SystemExit("GITHUB_TOKEN or --issues-json is required")
    market = compile_market(issues, repo=args.repo)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "market.json").write_text(json.dumps(market, indent=2) + "\n", encoding="utf-8")
    (args.output / "index.html").write_text(render_html(market), encoding="utf-8")
    print(json.dumps(market["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
