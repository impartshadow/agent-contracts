"""Repo-agnostic agent governance scanner.

Unlike ``score`` (which measures whether a repository has adopted
agent-contracts itself), ``scan`` measures *observable governance signals* in
any agent repository, regardless of which tools it uses. The score is a
mechanical, reproducible read of file structure and source text — it is not a
correctness proof and makes no claim that the agent behaves safely at runtime.
It measures whether the governance *surface* a reliable agent needs is present.

Seven dimensions, 100 points total:

- tests_and_ci      (20): a test suite plus CI that runs it
- tool_governance   (20): permission/allowlist/approval/human-in-loop gating
- secret_safety     (15): secrets ignored by git, no obvious hardcoded keys
- dependency_pinning(10): a lockfile or pinned dependency manifest
- eval_harness      (15): an eval / benchmark / labeled-corpus surface
- observability     (10): logging / audit / tracing
- resilience        (10): retry / backoff / fallback / escalation

Each dimension reports the concrete evidence (matched paths/patterns) so a
score is always defensible and reproducible from a clean clone.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Union

_SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "site-packages",
    ".next",
    ".cache",
    "vendor",
}

_SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".rb",
    ".java",
    ".kt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".cfg",
    ".ini",
    ".md",
    ".txt",
    ".sh",
}

_MAX_FILE_BYTES = 512 * 1024
_MAX_FILES_SCANNED = 4000


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _badge_color(score: int) -> str:
    if score >= 90:
        return "brightgreen"
    if score >= 80:
        return "green"
    if score >= 70:
        return "yellowgreen"
    if score >= 60:
        return "yellow"
    return "red"


def _badge_url(score: int) -> str:
    return (
        "https://img.shields.io/badge/"
        f"agent%20governance-{score}%2F100-{_badge_color(score)}"
    )


def _iter_files(root: Path) -> Iterable[Path]:
    count = 0
    for path in sorted(root.rglob("*")):
        if count >= _MAX_FILES_SCANNED:
            return
        if path.is_dir():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        count += 1
        yield path


def _read_text(path: Path) -> str:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, ValueError):
        return ""


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# Hardcoded-secret heuristics. Deliberately conservative to limit false
# positives; matches obvious literal keys, not env lookups.
_SECRET_PATTERNS = [
    re.compile(r"(?:sk|pk)-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{30,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(
        r"(?i)(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9/+_\-]{16,}['\"]"
    ),
]

_PLACEHOLDER = re.compile(
    r"(?i)(your|example|placeholder|xxx+|<[^>]+>|changeme|dummy|fake|test|sample|redacted)"
)


def _component(name: str, points: int, max_points: int, evidence: list[str], note: str) -> dict[str, Any]:
    return {
        "name": name,
        "points": max(0, min(points, max_points)),
        "max_points": max_points,
        "evidence": evidence[:8],
        "note": note,
    }


def scan_repository(root: Union[str, Path]) -> dict[str, Any]:
    """Score observable governance signals in any agent repository."""

    base = Path(root)
    files: list[Path] = list(_iter_files(base))
    rel_paths = [_rel(base, p) for p in files]
    lower_paths = [p.lower() for p in rel_paths]

    # Cache source text for the heuristic passes.
    text_blobs: dict[str, str] = {}
    for path, rel in zip(files, rel_paths):
        if path.suffix.lower() in _SOURCE_SUFFIXES:
            text_blobs[rel] = _read_text(path)

    components = [
        _score_tests_ci(rel_paths, lower_paths, text_blobs),
        _score_tool_governance(text_blobs),
        _score_secret_safety(base, rel_paths, lower_paths, text_blobs),
        _score_dependency_pinning(base, rel_paths, lower_paths, text_blobs),
        _score_eval_harness(lower_paths, text_blobs),
        _score_observability(text_blobs),
        _score_resilience(text_blobs),
    ]

    score = sum(c["points"] for c in components)
    return {
        "score": score,
        "grade": _grade(score),
        "passed": score >= 70,
        "files_scanned": len(files),
        "badge_url": _badge_url(score),
        "badge_endpoint": {
            "schemaVersion": 1,
            "label": "agent governance",
            "message": f"{score}/100",
            "color": _badge_color(score),
        },
        "badge_markdown": f"![Agent governance: {score}/100]({_badge_url(score)})",
        "components": components,
    }


def _has_any(lower_paths: list[str], needles: Iterable[str]) -> list[str]:
    hits = []
    for p in lower_paths:
        if any(n in p for n in needles):
            hits.append(p)
    return hits


def _grep(text_blobs: dict[str, str], pattern: re.Pattern[str], limit: int = 8) -> list[str]:
    hits = []
    for rel, blob in text_blobs.items():
        if pattern.search(blob):
            hits.append(rel)
            if len(hits) >= limit:
                break
    return hits


def _score_tests_ci(
    rel_paths: list[str], lower_paths: list[str], text_blobs: dict[str, str]
) -> dict[str, Any]:
    test_files = [
        p
        for p in lower_paths
        if (
            "/test" in p
            or p.startswith("test")
            or p.endswith("_test.py")
            or p.endswith(".test.ts")
            or p.endswith(".test.js")
            or p.endswith(".spec.ts")
            or "/spec/" in p
        )
    ]
    ci_files = [p for p in lower_paths if ".github/workflows/" in p or p in {".gitlab-ci.yml", "circle.yml"} or ".circleci/" in p]
    ci_runs_tests = []
    for rel in [r for r in text_blobs if ".github/workflows/" in r.lower() or ".gitlab-ci" in r.lower()]:
        blob = text_blobs[rel].lower()
        if any(k in blob for k in ("pytest", "npm test", "go test", "cargo test", "unittest", "jest", "vitest", "tox")):
            ci_runs_tests.append(rel)

    points = 0
    evidence: list[str] = []
    if test_files:
        points += 10
        evidence.extend(test_files[:3])
    if ci_runs_tests:
        points += 10
        evidence.extend(ci_runs_tests[:2])
    elif ci_files:
        points += 5
        evidence.extend(ci_files[:2])

    note = "test suite + CI running it" if test_files and ci_runs_tests else (
        "partial: tests or CI present, not both wired" if (test_files or ci_files) else "no tests/CI detected"
    )
    return _component("tests_and_ci", points, 20, evidence, note)


_GOVERNANCE = re.compile(
    r"(?i)\b("
    r"allow_?list|allowlist|deny_?list|permission|approval|approve|"
    r"human[_\- ]?in[_\- ]?the[_\- ]?loop|hitl|require_?confirm|confirm_?before|"
    r"guard|policy|sandbox|scope[ds]?|authoriz|gate(?:keeper|d)?"
    r")\b"
)


def _score_tool_governance(text_blobs: dict[str, str]) -> dict[str, Any]:
    hits = _grep(text_blobs, _GOVERNANCE)
    distinct = len(hits)
    if distinct >= 4:
        points = 20
    elif distinct >= 2:
        points = 13
    elif distinct == 1:
        points = 6
    else:
        points = 0
    note = (
        "permission/approval/guard gating present across modules"
        if points >= 13
        else "minimal or no explicit tool-governance signals"
    )
    return _component("tool_governance", points, 20, hits, note)


def _score_secret_safety(
    base: Path, rel_paths: list[str], lower_paths: list[str], text_blobs: dict[str, str]
) -> dict[str, Any]:
    points = 0
    evidence: list[str] = []

    gitignore = base / ".gitignore"
    ignores_secrets = False
    if gitignore.exists():
        gi = _read_text(gitignore).lower()
        if any(tok in gi for tok in (".env", "secret", "credential", "*.pem", "*.key")):
            ignores_secrets = True
    if ignores_secrets:
        points += 8
        evidence.append(".gitignore covers secrets")

    # Penalize obvious hardcoded secrets in tracked source.
    leaks: list[str] = []
    for rel, blob in text_blobs.items():
        if rel.lower().endswith((".md", ".txt")):
            continue
        for pat in _SECRET_PATTERNS:
            m = pat.search(blob)
            if m and not _PLACEHOLDER.search(m.group(0)):
                leaks.append(rel)
                break
    if leaks:
        evidence.extend(f"possible hardcoded secret: {p}" for p in leaks[:3])
    else:
        points += 7
        evidence.append("no obvious hardcoded secrets in tracked source")

    note = "secrets ignored + no hardcoded keys" if points == 15 else (
        "secret hygiene gaps detected" if leaks else "no secret-ignore rules found"
    )
    return _component("secret_safety", points, 15, evidence, note)


def _score_dependency_pinning(
    base: Path, rel_paths: list[str], lower_paths: list[str], text_blobs: dict[str, str]
) -> dict[str, Any]:
    lockfiles = _has_any(
        lower_paths,
        (
            "poetry.lock",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "uv.lock",
            "cargo.lock",
            "go.sum",
            "pipfile.lock",
            "requirements.lock",
        ),
    )
    points = 0
    evidence: list[str] = []
    if lockfiles:
        points = 10
        evidence.extend(lockfiles[:3])
    else:
        # Pinned requirements.txt (== specifiers) counts for partial credit.
        pinned = []
        for rel, blob in text_blobs.items():
            if rel.lower().endswith("requirements.txt") and "==" in blob:
                pinned.append(rel)
        if pinned:
            points = 7
            evidence.extend(pinned[:3])
    note = "lockfile present" if points == 10 else (
        "pinned manifest, no lockfile" if points == 7 else "no dependency pinning detected"
    )
    return _component("dependency_pinning", points, 10, evidence, note)


def _score_eval_harness(lower_paths: list[str], text_blobs: dict[str, str]) -> dict[str, Any]:
    eval_paths = _has_any(
        lower_paths,
        ("eval", "benchmark", "/bench", "corpus", "golden", "fixtures/", "regression"),
    )
    # Filter noise: "eval" matches "evaluate" in random files; require a dir-ish hit.
    strong = [p for p in eval_paths if any(seg in p for seg in ("eval", "benchmark", "corpus", "golden"))]
    if strong:
        points = 15
        note = "eval/benchmark/corpus surface present"
    elif eval_paths:
        points = 7
        note = "weak eval signal (fixtures/regression only)"
    else:
        points = 0
        note = "no eval or benchmark harness detected"
    return _component("eval_harness", points, 15, eval_paths, note)


_OBSERVABILITY = re.compile(
    r"(?i)\b(logging\.|logger|getlogger|structlog|loguru|opentelemetry|"
    r"otel|trace\(|tracing|audit_?log|metrics?\.|prometheus|wandb|langsmith|langfuse)\b"
)


def _score_observability(text_blobs: dict[str, str]) -> dict[str, Any]:
    hits = _grep(text_blobs, _OBSERVABILITY)
    if len(hits) >= 3:
        points = 10
    elif hits:
        points = 5
    else:
        points = 0
    note = "logging/tracing/audit present" if points else "no observability signals"
    return _component("observability", points, 10, hits, note)


_RESILIENCE = re.compile(
    r"(?i)\b(retry|retries|backoff|tenacity|exponential|fallback|"
    r"circuit_?breaker|escalat|max_?attempts|on_?error|except\b|try:)\b"
)


def _score_resilience(text_blobs: dict[str, str]) -> dict[str, Any]:
    hits = _grep(text_blobs, _RESILIENCE)
    strong = _grep(text_blobs, re.compile(r"(?i)\b(retry|backoff|tenacity|fallback|circuit_?breaker|escalat|max_?attempts)\b"))
    if len(strong) >= 2:
        points = 10
    elif strong or len(hits) >= 3:
        points = 5
    else:
        points = 0
    note = "explicit retry/fallback/escalation logic" if points == 10 else (
        "basic error handling only" if points else "no resilience signals"
    )
    return _component("resilience", points, 10, hits, note)


def render_scan_markdown(payload: dict[str, Any], project: str | None = None) -> str:
    title = f"# Agent Governance Scan — {project}" if project else "# Agent Governance Scan"
    lines = [
        title,
        "",
        f"**Score: {payload['score']}/100 (grade {payload['grade']})**",
        "",
        payload["badge_markdown"],
        "",
        "| Dimension | Points | Signal |",
        "|---|---:|---|",
    ]
    for c in payload["components"]:
        lines.append(f"| {c['name']} | {c['points']} / {c['max_points']} | {c['note']} |")
    lines.extend(
        [
            "",
            "This scan is mechanical and reproducible from a clean clone. It reads "
            "observable governance *surface* (tests, gating, secret hygiene, pinning, "
            "evals, observability, resilience) — not runtime behavior. Missing a "
            "dimension earns zero; there is no credit for a story about what the agent "
            "probably does.",
        ]
    )
    return "\n".join(lines)
