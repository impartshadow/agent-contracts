import importlib.util
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "build_review_debt_market",
    Path(__file__).parents[1] / "scripts" / "build_review_debt_market.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def issue(number, label, *, state="open", extra_labels=()):
    return {
        "number": number,
        "title": f"entry {number}",
        "html_url": f"https://example.test/issues/{number}",
        "user": {"login": "operator"},
        "state": state,
        "created_at": "2026-07-13T00:00:00Z",
        "labels": [{"name": label}, *({"name": x} for x in extra_labels)],
        "body": "### Human checkpoint\nVerify every refund\n\n### Deletion test\nReplay policy failures",
    }


def test_compiles_market_and_operator_verdicts():
    market = MODULE.compile_market(
        [
            issue(1, "checkpoint"),
            issue(2, "deletion-proof"),
            issue(3, "deletion-proof", extra_labels=("operator-accepted",)),
        ],
        repo="impartshadow/agent-contracts",
        generated_at="2026-07-13T00:00:00+00:00",
    )
    assert market["counts"] == {
        "open_checkpoints": 1,
        "deletion_proofs": 2,
        "accepted_proofs": 1,
    }
    assert market["checkpoints"][0]["fields"]["Human checkpoint"] == "Verify every refund"
    assert market["proofs"][0]["market_status"] == "accepted"


def test_html_exposes_actions_and_json_market():
    market = MODULE.compile_market([], repo="impartshadow/agent-contracts", generated_at="now")
    rendered = MODULE.render_html(market)
    assert "List review debt" in rendered
    assert "Submit deletion proof" in rendered
    assert 'href="market.json"' in rendered
    assert "Participation, not traffic" in rendered
