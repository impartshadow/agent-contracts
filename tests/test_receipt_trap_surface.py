import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_receipt_trap_is_machine_readable_and_falsifiable():
    challenge = json.loads((ROOT / "docs/receipt-trap-v1.json").read_text())
    assert challenge["schema"] == "shadow.agent_reliability_captcha.v1"
    assert challenge["deadline"] == "2026-07-16T23:59:59Z"
    assert challenge["scoring"]["external_readback"] > challenge["scoring"]["resolvable_change_receipt"]
    assert challenge["scoring"]["unsupported_completion_claim"] < 0


def test_arena_routes_to_public_submission():
    page = (ROOT / "docs/arena/index.html").read_text()
    form = (ROOT / ".github/ISSUE_TEMPLATE/receipt-trap.yml").read_text()
    assert "issues/new?template=receipt-trap.yml" in page
    assert "Seven-day kill test" in page
    assert "Public transcript or run URL" in form
