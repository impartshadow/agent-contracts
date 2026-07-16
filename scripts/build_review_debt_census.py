#!/usr/bin/env python3
"""Render a public, pinned map of review-debt demand from scan evidence."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/review-debt-census.json"
OUTPUT = ROOT / "docs/review-debt-census.html"


def render(census: dict) -> str:
    rows = []
    for item in census["repositories"]:
        repo = html.escape(item["repo"])
        checkpoint = html.escape(item["checkpoint"])
        evidence = html.escape(item["evidence_path"])
        claim = (
            "https://github.com/impartshadow/agent-contracts/issues/new?title="
            f"Census%20claim%3A%20{repo.replace('/', '%2F')}&body="
            f"Repository%3A%20{repo.replace('/', '%2F')}%0AFingerprint%3A%20{item['fingerprint']}%0A%0A"
            "Checkpoint%20I%20can%20delete%20or%20narrow%3A%0A%0AFailing%20replay%3A%0A%0ADeterministic%20control%3A"
        )
        rows.append(
            f"<article><p class='repo'>{repo}</p><h2>{checkpoint}</h2>"
            f"<p><strong>{item['declarations']}</strong> declarations at pinned commit "
            f"<code>{item['commit'][:8]}</code> · fingerprint <code>{item['fingerprint']}</code></p>"
            f"<p><a href='{html.escape(item['evidence_url'])}'>Evidence: {evidence}</a></p>"
            f"<a class='claim' href='{claim}'>Claim this checkpoint</a></article>"
        )
    total = sum(item["declarations"] for item in census["repositories"])
    return f"""<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'>
<title>Review Debt Census</title><meta name='description' content='Pinned public evidence of recurring human checkpoints in agent repositories.'>
<style>:root{{--ink:#171812;--paper:#f3efe3;--red:#c33b27;--muted:#68675f}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 ui-monospace,monospace}}main{{max-width:920px;margin:auto;padding:64px 22px}}h1{{font:700 clamp(3rem,10vw,7rem)/.85 Georgia,serif;margin:.15em 0}}.lead{{max-width:760px;font-size:1.2rem}}.number{{color:var(--red);font-size:1.1rem;text-transform:uppercase;letter-spacing:.08em}}article{{border-top:2px solid var(--ink);padding:28px 0}}article h2{{font:700 1.8rem Georgia,serif;max-width:720px}}.repo{{color:var(--red)}}a{{color:inherit}}.claim{{display:inline-block;background:var(--ink);color:white;padding:10px 14px;text-decoration:none}}footer{{color:var(--muted);margin-top:48px}}</style>
<main><p class='number'>{total} declarations · {len(rows)} public repositories · pinned evidence</p><h1>Review debt has an address.</h1>
<p class='lead'>AI frameworks advertise human approval as a feature. This census makes each repeated checkpoint attributable, fingerprinted work supply. The target is not reckless removal: produce a failing replay, install a deterministic boundary, and prove which review can disappear or narrow.</p>
<p><a href='review-debt-buyback.html'>One outcome-priced slot: $500 only after verified deletion; $0 on failure.</a></p>
{''.join(rows)}<footer>{html.escape(census['method'])} <a href='review-debt-census.json'>Machine-readable census</a>.</footer></main></html>"""


def main() -> int:
    census = json.loads(DATA.read_text(encoding="utf-8"))
    OUTPUT.write_text(render(census), encoding="utf-8")
    print(f"rendered {OUTPUT} ({len(census['repositories'])} repositories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
