#!/usr/bin/env python3
"""Generate 1200x630 Open Graph share images for the governance index.

Every backlink into the index — the 29 live badges, the Substack crosslinks, any
X/Slack/Discord/HN drop of a leaderboard or per-framework URL — renders whatever
``og:image`` the page declares. Until now the pages declared none, so a
``summary_large_image`` card rendered blank and a plain link elsewhere. This
turns each framework's score into a self-contained visual card: the share itself
becomes an ad for the index and funnels to the weekly-delta Substack.

Rendered mechanically from the same ``leaderboard_history.jsonl`` run the report
cards use, so the image and the page never drift. Regenerated on every scan via
``gen_framework_pages.generate()``.

Usage: python scripts/gen_og_cards.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent_contracts import history as history_mod  # noqa: E402

HISTORY_PATH = REPO_ROOT / history_mod.DEFAULT_HISTORY_FILENAME
OUT_DIR = REPO_ROOT / "docs" / "og"

W, H = 1200, 630
BG = (13, 17, 23)
PANEL = (22, 27, 34)
LINE = (48, 54, 61)
FG = (230, 237, 243)
MUTED = (139, 148, 158)
ACCENT = (88, 166, 255)

GRADE_COLORS = {
    "A": (63, 185, 80),
    "B": (88, 166, 255),
    "C": (210, 153, 34),
    "D": (248, 81, 73),
    "F": (248, 81, 73),
}

DIMENSIONS = [
    ("tests_and_ci", 20),
    ("tool_governance", 20),
    ("secret_safety", 15),
    ("eval_harness", 15),
    ("dependency_pinning", 10),
    ("observability", 10),
    ("resilience", 10),
]
DIM_MAX = {n: mx for n, mx in DIMENSIONS}

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


def _grade_color(grade: str) -> tuple[int, int, int]:
    return GRADE_COLORS.get(grade, GRADE_COLORS["D"])


def _rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _bar_color(pts: int, mx: int) -> tuple[int, int, int]:
    if pts >= mx:
        return GRADE_COLORS["A"]
    if pts == 0:
        return GRADE_COLORS["D"]
    return GRADE_COLORS["C"]


def _scan_date() -> str:
    return datetime.now(timezone.utc).strftime("%b %-d, %Y")


def _footer(draw, date_str: str):
    f_small = _font("DejaVuSans.ttf", 22)
    draw.line([(60, H - 78), (W - 60, H - 78)], fill=LINE, width=1)
    draw.text((60, H - 58), "Shadow Agent Governance Index", font=f_small, fill=MUTED)
    right = f"re-scanned {date_str} · echofromshadow.substack.com"
    w = draw.textlength(right, font=f_small)
    draw.text((W - 60 - w, H - 58), right, font=f_small, fill=ACCENT)


def _label(draw):
    f_label = _font("DejaVuSansMono.ttf", 20)
    draw.text((60, 52), "SHADOW · AGENT GOVERNANCE INDEX", font=f_label, fill=MUTED)


def render_framework_card(rec: dict, date_str: str) -> Image.Image:
    project = rec["project"]
    score = rec["score"]
    grade = rec["grade"]
    comps = rec.get("components", {})
    gcolor = _grade_color(grade)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _label(d)

    # Repo name
    f_owner = _font("DejaVuSansMono.ttf", 30)
    f_repo = _font("DejaVuSans-Bold.ttf", 62)
    owner, _, repo = project.partition("/")
    d.text((60, 108), f"{owner}/", font=f_owner, fill=MUTED)
    repo_disp = repo if len(repo) <= 22 else repo[:21] + "…"
    d.text((60, 146), repo_disp, font=f_repo, fill=FG)

    d.text((60, 226), "Production-governance score", font=_font("DejaVuSans.ttf", 26), fill=MUTED)

    # Big score + grade badge
    f_score = _font("DejaVuSans-Bold.ttf", 150)
    d.text((60, 268), str(score), font=f_score, fill=FG)
    sw = d.textlength(str(score), font=f_score)
    d.text((60 + sw + 8, 372), "/100", font=_font("DejaVuSans.ttf", 44), fill=MUTED)

    # Grade badge (top-right)
    bx0, by0 = W - 260, 120
    _rounded(d, [bx0, by0, W - 60, by0 + 200], 24, fill=(gcolor[0] // 6 + 20, gcolor[1] // 6 + 24, gcolor[2] // 6 + 30), outline=gcolor, width=3)
    f_grade = _font("DejaVuSans-Bold.ttf", 140)
    gw = d.textlength(grade, font=f_grade)
    d.text((bx0 + (200 - gw) / 2, by0 + 22), grade, font=f_grade, fill=gcolor)

    # Dimension bars (right column, all 7)
    dx, dy = 640, 300
    dw = 500
    f_dim = _font("DejaVuSansMono.ttf", 19)
    for i, (name, mx) in enumerate(DIMENSIONS):
        pts = comps.get(name, 0)
        y = dy + i * 30
        d.text((dx, y - 2), name, font=f_dim, fill=MUTED)
        pts_txt = f"{pts}/{mx}"
        pw = d.textlength(pts_txt, font=f_dim)
        d.text((dx + dw - pw, y - 2), pts_txt, font=f_dim, fill=FG)
        # bar
        bar_y = y + 21
        _rounded(d, [dx, bar_y, dx + dw, bar_y + 7], 3, fill=(33, 38, 45))
        frac = max(0.0, min(1.0, pts / mx))
        if frac > 0:
            _rounded(d, [dx, bar_y, dx + dw * frac, bar_y + 7], 3, fill=_bar_color(pts, mx))

    _footer(d, date_str)
    return img


def render_leaderboard_card(records: list[dict], date_str: str) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _label(d)

    f_h1 = _font("DejaVuSans-Bold.ttf", 58)
    d.text((60, 104), f"{len(records)} agent frameworks,", font=f_h1, fill=FG)
    d.text((60, 168), "scored for production governance", font=f_h1, fill=FG)
    d.text(
        (60, 250),
        "Mechanical, reproducible scores — re-scanned weekly. No vibes.",
        font=_font("DejaVuSans.ttf", 28),
        fill=MUTED,
    )

    # Top rows
    top = sorted(records, key=lambda r: r["score"], reverse=True)[:5]
    f_row = _font("DejaVuSansMono.ttf", 26)
    y = 320
    for r in top:
        gcolor = _grade_color(r["grade"])
        d.text((60, y), r["project"], font=f_row, fill=FG)
        badge = f"{r['score']}/100  {r['grade']}"
        bw = d.textlength(badge, font=f_row)
        d.text((W - 60 - bw, y), badge, font=f_row, fill=gcolor)
        y += 44

    _footer(d, date_str)
    return img


def generate(records: list[dict] | None = None) -> int:
    """Render one OG card per framework + a leaderboard card + a default card."""
    if records is None:
        hist = history_mod.load_history(HISTORY_PATH)
        ids = history_mod.run_ids(hist)
        if not ids:
            print("no runs in history; nothing to generate", file=sys.stderr)
            return 0
        latest = history_mod.run_map(hist, ids[-1])
        records = list(latest.values())
    else:
        norm = []
        for r in records:
            comps = r.get("components", {})
            if isinstance(comps, list):
                comps = {c["name"]: c["points"] for c in comps}
            norm.append(
                {"project": r["project"], "score": r["score"], "grade": r["grade"], "components": comps}
            )
        records = norm

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = _scan_date()
    written = 0
    for rec in records:
        slug = rec["project"].replace("/", "__")
        render_framework_card(rec, date_str).save(OUT_DIR / f"{slug}.png", "PNG")
        written += 1

    lb = render_leaderboard_card(records, date_str)
    lb.save(OUT_DIR / "leaderboard.png", "PNG")
    lb.save(OUT_DIR / "default.png", "PNG")
    print(f"wrote {written} framework OG cards + leaderboard + default to {OUT_DIR}", flush=True)
    return written


if __name__ == "__main__":
    raise SystemExit(0 if generate() else 1)
