import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_buyback_is_outcome_priced_and_terminal():
    offer = json.loads((ROOT / "docs/review-debt-buyback.json").read_text())
    assert offer["capacity"] == 1
    assert offer["price_after_verified_deletion_usd"] == 500
    assert offer["price_if_deletion_test_fails_usd"] == 0
    assert offer["acceptance_deadline"] == "2026-07-23T23:59:59Z"
    assert len(offer["settlement_receipts"]) == 4
    assert "not extended" in offer["falsifier"]


def test_public_surface_routes_to_structured_intake():
    page = (ROOT / "docs/review-debt-buyback.html").read_text()
    assert "Delete the review first. Pay after." in page
    assert "Repeated%20human%20review" in page
    assert "review-debt-buyback.json" in page
