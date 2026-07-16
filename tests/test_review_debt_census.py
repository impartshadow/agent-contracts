import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_review_debt_census import render


def test_census_is_pinned_attributable_and_claimable():
    census = json.loads((ROOT / "docs/review-debt-census.json").read_text())
    assert len(census["repositories"]) >= 3
    for item in census["repositories"]:
        assert len(item["commit"]) == 40
        assert item["fingerprint"]
        assert item["evidence_url"].startswith(f"https://github.com/{item['repo']}/blob/{item['commit']}/")
    page = render(census)
    assert "Claim this checkpoint" in page
    assert "failing replay" in page
    assert "review-debt-census.json" in page
