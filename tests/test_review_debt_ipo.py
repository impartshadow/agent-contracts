import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.review_debt_ipo import prospectus, scan


def test_scan_finds_declared_checkpoints_and_skips_dependencies(tmp_path: Path):
    (tmp_path / "README.md").write_text("A human must approve refunds.\nManual verification is required.\n")
    hidden = tmp_path / "node_modules"
    hidden.mkdir()
    (hidden / "noise.js").write_text("human must review")
    findings = scan(tmp_path)
    assert [(row["path"], row["line"]) for row in findings] == [("README.md", 1), ("README.md", 2)]


def test_prospectus_is_stable_and_demands_runnable_proof():
    findings = [{"path": "policy.md", "line": 4, "excerpt": "Human must approve"}]
    first = prospectus(findings)
    second = prospectus(findings)
    assert first["fingerprint"] == second["fingerprint"]
    assert f"review-debt-ipo:{first['fingerprint']}" in first["body"]
    assert "failing test or replay" in first["body"]
    assert "deterministic control" in first["body"]
