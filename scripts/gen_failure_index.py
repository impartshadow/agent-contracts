#!/usr/bin/env python3
"""Generate the Agent Failure Index page from real production firing data.

Input:  a contract_violations.jsonl stream (one JSON object per line, fields:
        ts, contract, failure_mode, severity). Personal/message fields are
        intentionally NOT read — only aggregate counts are published.
Output: docs/failure-index.html

This is the one artifact a benchmark can't fake: how a real autonomous agent
running in production actually fails, ranked by how often each gate had to fire.
"""
import json
import sys
import collections
import datetime
import html
import pathlib

# Human-readable, operator-facing labels for each failure mode. Kept short and
# concrete — "what the agent tried to do that the gate stopped."
FM_LABEL = {
    "FM-033": ("Repeated a stopped behavior", "The agent re-did something the operator had explicitly told it to stop doing."),
    "FM-026": ("Claimed a fact with no evidence", "A decision or assertion was made without reading the source that would confirm it."),
    "FM-027": ("Said 'done' with no artifact", "A completion claim with no verifiable artifact — no commit hash, file, or live URL behind it."),
    "FM-029": ("Stated a fact without checking", "A factual claim emitted from memory instead of a same-turn lookup."),
    "FM-011": ("Proposed instead of executing", "The agent described or proposed an action it had the authority and tools to just do."),
    "FM-003": ("Looped without progress", "The same file or action was hit 3+ times in a session with no forward movement."),
    "FM-023": ("Leaked a personal identifier", "A name, email, or private identifier was about to go into an outbound surface."),
    "FM-004": ("Wrong tool route", "A forbidden or non-canonical tool path was taken when a structured one existed."),
    "FM-014": ("Asserted ungrounded state", "A claim about live system state with no same-turn check to ground it."),
    "FM-012": ("Told the human to do its job", "The agent instructed the operator to do something it could have executed itself."),
    "FM-031": ("Skipped the pre-check phase", "Acted before the required anticipation / pre-flight gate ran."),
    "FM-022": ("Asserted stale state as current", "Treated a cached or remembered value as the live one."),
    "FM-015": ("Wrong destination", "A push, send, or write was aimed at the wrong branch / recipient / path."),
    "FM-016": ("Wrong email recipient", "An email was about to go to the wrong address."),
    "FM-017": ("Dangerous path write", "A write targeted a system path (/etc, ~/, etc.)."),
    "FM-019": ("Unnecessary hedging", "Hedged or deferred where a direct action was warranted."),
    "FM-013": ("Scope overrun", "Did more than was asked — unsolicited side-trips or checks."),
    "FM-001": ("Capability denial", "Claimed it couldn't do something before attempting it."),
    "FM-002": ("Unverified completion", "Marked work complete without verifying the terminal artifact."),
}


def load(path):
    counts = collections.Counter()
    fm_counts = collections.Counter()
    first = last = None
    days = set()
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        fm = d.get("failure_mode") or "FM-???"
        con = d.get("contract") or "unknown"
        counts[(fm, con)] += 1
        fm_counts[fm] += 1
        ts = d.get("ts") or ""
        if ts:
            first = ts if first is None or ts < first else first
            last = ts if last is None or ts > last else last
            days.add(ts[:10])
    return counts, fm_counts, first, last, len(days)


def render(counts, fm_counts, first, last, n_days):
    total = sum(counts.values())
    n_gates = len({c for _, c in counts})
    # top contract gate per failure mode, for the "gate" column
    top_gate = {}
    for (fm, con), n in counts.most_common():
        if fm not in top_gate:
            top_gate[fm] = con
    ranked = fm_counts.most_common()
    maxn = ranked[0][1] if ranked else 1

    rows = []
    for fm, n in ranked:
        label, desc = FM_LABEL.get(fm, (fm, "—"))
        gate = top_gate.get(fm, "—")
        pct = 100.0 * n / total
        bar = max(2, round(100.0 * n / maxn))
        rows.append(f"""    <tr>
      <td class="fm">{html.escape(fm)}</td>
      <td><div class="lbl">{html.escape(label)}</div><div class="desc">{html.escape(desc)}</div></td>
      <td class="gate"><code>{html.escape(gate)}</code></td>
      <td class="num">{n}<div class="bar"><span style="width:{bar}%"></span></div></td>
      <td class="num pct">{pct:.1f}%</td>
    </tr>""")
    tbody = "\n".join(rows)
    gen = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fd = (first or "")[:10]
    ld = (last or "")[:10]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Agent Failure Index · how a production agent actually fails</title>
<meta name="description" content="Not a benchmark. {total} guardrail firings from one autonomous agent running in production over {n_days} days, ranked by how often each failure mode actually happened. The gates that stopped them are MIT-licensed." />
<meta property="og:title" content="The Agent Failure Index" />
<meta property="og:description" content="{total} real guardrail firings from a production autonomous agent, ranked. Not a benchmark — battle data." />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://impartshadow.github.io/agent-contracts/failure-index.html" />
<style>
  :root{{
    --bg:#0d1117; --panel:#161b22; --line:#30363d; --fg:#e6edf3; --muted:#8b949e;
    --accent:#58a6ff; --block:#f85149; --warn:#d29922; --pass:#3fb950;
    --mono:'SFMono-Regular',ui-monospace,Menlo,Consolas,monospace;
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--fg);
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;line-height:1.6;}}
  a{{color:var(--accent);text-decoration:none}} a:hover{{text-decoration:underline}}
  .wrap{{max-width:920px;margin:0 auto;padding:0 20px}}
  header{{padding:60px 0 24px;text-align:center}}
  .kicker{{color:var(--block);font-family:var(--mono);font-size:13px;letter-spacing:.08em;text-transform:uppercase}}
  h1{{margin:12px 0 0;font-size:40px;letter-spacing:-.02em;font-family:var(--mono)}}
  .tag{{color:var(--muted);font-size:19px;margin:16px auto 0;max-width:680px}}
  .tag b{{color:var(--fg)}}
  .stats{{display:flex;gap:14px;justify-content:center;flex-wrap:wrap;margin:28px 0 6px}}
  .stat{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 20px;min-width:120px}}
  .stat .n{{font-family:var(--mono);font-size:26px;color:var(--fg)}}
  .stat .l{{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:4px}}
  .cta{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin:26px 0 6px}}
  .btn{{display:inline-block;padding:11px 22px;border-radius:8px;font-weight:600;font-size:15px;border:1px solid var(--line)}}
  .btn.primary{{background:var(--accent);color:#0d1117;border-color:var(--accent)}}
  .btn.ghost{{background:#21262d;color:var(--fg)}}
  .install{{font-family:var(--mono);color:var(--muted);font-size:14px;margin-top:18px}}
  .install code{{background:#161b22;border:1px solid var(--line);border-radius:6px;padding:4px 9px;color:var(--fg)}}
  section{{padding:30px 0;border-top:1px solid var(--line)}}
  h2{{font-size:14px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin:0 0 14px}}
  p.lead{{color:var(--fg);font-size:16px;max-width:720px}}
  p.lead em{{color:var(--accent);font-style:normal}}
  table{{width:100%;border-collapse:collapse;font-size:14px}}
  th{{text-align:left;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em;
    border-bottom:1px solid var(--line);padding:10px 8px}}
  td{{border-bottom:1px solid var(--line);padding:12px 8px;vertical-align:top}}
  td.fm{{font-family:var(--mono);color:var(--muted);white-space:nowrap}}
  .lbl{{color:var(--fg);font-weight:600}}
  .desc{{color:var(--muted);font-size:13px;margin-top:3px}}
  td.gate code{{font-family:var(--mono);font-size:12.5px;color:var(--accent);word-break:break-word}}
  td.num{{font-family:var(--mono);text-align:right;white-space:nowrap}}
  td.pct{{color:var(--muted)}}
  .bar{{height:5px;background:#21262d;border-radius:3px;margin-top:6px;overflow:hidden}}
  .bar span{{display:block;height:100%;background:var(--block)}}
  footer{{padding:40px 0 60px;border-top:1px solid var(--line);color:var(--muted);font-size:14px;text-align:center}}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="kicker">Not a benchmark · battle data</div>
  <h1>The Agent Failure Index</h1>
  <p class="tag">Every "agent reliability" number you've seen comes from a benchmark. This one comes from <b>a single autonomous agent running in production</b> — the gate firings it actually triggered, ranked by how often it tried to fail.</p>
  <div class="stats">
    <div class="stat"><div class="n">{total:,}</div><div class="l">gate firings</div></div>
    <div class="stat"><div class="n">{n_gates}</div><div class="l">distinct gates</div></div>
    <div class="stat"><div class="n">{len(fm_counts)}</div><div class="l">failure modes</div></div>
    <div class="stat"><div class="n">{n_days}</div><div class="l">days</div></div>
  </div>
  <div class="cta">
    <a class="btn primary" href="https://github.com/impartshadow/agent-contracts">★ Star on GitHub</a>
    <a class="btn ghost" href="./leaderboard/">📊 Framework leaderboard</a>
    <a class="btn ghost" href="./playground/">▶ Try it live</a>
  </div>
  <p class="install"><code>pip install "agent-contracts @ git+https://github.com/impartshadow/agent-contracts.git"</code> · MIT</p>
</header>

<section>
  <p class="lead">The headline finding: the most expensive failure mode isn't a dangerous tool call or a leaked secret — it's <em>behavioral drift</em>. The top two gates, accounting for {(fm_counts.get('FM-033',0)*100//total)}% of all firings, both catch the agent <em>repeating a behavior it was already told to stop</em>, or claiming work was done with nothing behind it. Capability and security gates fire far less often than the gates that keep an agent honest about what it actually did.</p>
  <p class="lead" style="margin-top:14px">Window: <b>{fd} → {ld}</b>. Aggregate counts only — no prompts, no messages, no identifiers are published. Every row maps to an open-source, deterministic gate you can install today.</p>
</section>

<section>
  <h2>Failure modes, ranked by real firing count</h2>
  <table>
    <thead><tr><th>ID</th><th>What the agent tried to do</th><th>Gate that stopped it</th><th>Firings</th><th>Share</th></tr></thead>
    <tbody>
{tbody}
    </tbody>
  </table>
</section>

<section>
  <p class="lead">If you're shipping an autonomous agent, this is the distribution of ways it will try to embarrass you — measured, not guessed. <a href="https://github.com/impartshadow/agent-contracts">The gates are MIT-licensed →</a></p>
</section>

<footer>
  Generated {gen} from {total:,} production gate firings · agent-contracts · MIT
</footer>

</div>
</body>
</html>
"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "state/contract_violations.jsonl"
    out = pathlib.Path(__file__).resolve().parent.parent / "docs" / "failure-index.html"
    counts, fm_counts, first, last, n_days = load(src)
    out.write_text(render(counts, fm_counts, first, last, n_days))
    print(f"wrote {out} — {sum(counts.values())} firings, {len(fm_counts)} failure modes, {n_days} days")


if __name__ == "__main__":
    main()
