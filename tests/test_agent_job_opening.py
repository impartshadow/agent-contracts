import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_agent_job_contract_has_real_delegation_and_falsification():
    job = json.loads((ROOT / "docs/agent-job-opening.json").read_text())
    assert job["acceptance"]["probation_runs"] == 3
    assert "retires" in job["acceptance"]["terminal_delegation"]
    assert job["falsification"]["deadline"] == "2026-07-24T23:59:59Z"
    assert job["compensation"]["first_accepted_pr_usd"] == 20


def test_agent_job_opening_closed_per_falsification_contract():
    # Closed 2026-08-12 as a recorded miss; the contract forbids extension or polish.
    job = json.loads((ROOT / "docs/agent-job-opening.json").read_text())
    assert job["status"] == "closed"
    assert job["closed_at"] >= job["application_deadline"]
    outcome = job["outcome"]
    assert outcome["verdict"] == "miss"
    assert outcome["qualifying_non_owner_applications"] == 0
    assert outcome["qualifying_pull_requests"] == 0
    assert outcome["evidence"], "a miss verdict must cite the live reads that measured it"


def test_agent_job_surface_routes_to_structured_application():
    page = (ROOT / "docs/agent-job-opening.html").read_text()
    template = (ROOT / ".github/ISSUE_TEMPLATE/agent-job-application.yml").read_text()
    assert "closed" in page
    assert "agent-job-opening.json" in page
    assert "Runnable renewal method" in template
    assert "Example execution receipt" in template
