#!/usr/bin/env python3
"""Clone well-known public agent repos, scan them, and regenerate LEADERBOARD.md.

The leaderboard is only credible if it contains real, recognizable agent
projects scored by the same mechanical scanner anyone can run. This script:

1. shallow-clones a curated set of public agent repos into a temp dir,
2. runs ``scan_repository`` on each,
3. writes LEADERBOARD.md sorted by score, with reproduction commands.

Usage: python scripts/seed_leaderboard.py [--workdir DIR] [--keep]
"""

from __future__ import annotations

import argparse
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent_contracts.scan import scan_repository  # noqa: E402

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


def clone(repo: str, dest: Path) -> Path | None:
    url = f"https://github.com/{repo}.git"
    target = dest / repo.replace("/", "__")
    if target.exists():
        return target
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
        return None
    return target


def render_leaderboard(rows: list[dict]) -> str:
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
        "Scores are intentionally harsh. A missing dimension earns zero — there is no",
        "credit for a story about what the agent probably does.",
        "",
        "| Rank | Project | Score | Grade | Strongest | Weakest |",
        "|---:|---|---:|:--:|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        comps = r["components"]
        strongest = max(comps, key=lambda c: c["points"] / c["max_points"])
        weakest = min(comps, key=lambda c: c["points"] / c["max_points"])
        weakest_label = "—" if weakest["points"] == weakest["max_points"] else weakest["name"]
        lines.append(
            f"| {i} | [`{r['project']}`](https://github.com/{r['project']}) "
            f"| {r['score']}/100 | {r['grade']} "
            f"| {strongest['name']} | {weakest_label} |"
        )
    lines.extend(
        [
            "",
            "## Reproduce any score",
            "",
            "```bash",
            "pip install agent-contracts",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    workdir = Path(args.workdir) if args.workdir else Path(tempfile.mkdtemp(prefix="acscan_"))
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"workdir: {workdir}", flush=True)

    rows = []
    for repo in SEED_REPOS:
        path = clone(repo, workdir)
        if path is None:
            continue
        try:
            payload = scan_repository(path)
            payload["project"] = repo
            rows.append(payload)
            print(f"  {repo}: {payload['score']}/100 ({payload['grade']})", flush=True)
        finally:
            if not args.keep:
                shutil.rmtree(path, ignore_errors=True)

    if not rows:
        print("no repos scored", file=sys.stderr)
        return 1

    out = REPO_ROOT / "LEADERBOARD.md"
    out.write_text(render_leaderboard(rows), encoding="utf-8")
    print(f"wrote {out} with {len(rows)} entries", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
