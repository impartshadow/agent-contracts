from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_delegation_check_issue_form_has_falsifiable_inputs():
    form = (ROOT / ".github/ISSUE_TEMPLATE/delegation-check.yml").read_text()

    assert "labels:\n  - delegation-check" in form
    for field in ("workflow", "human_check", "failure", "consequence", "desired_ownership"):
        assert f"id: {field}" in form
    assert "required: true" in form
    assert "Public-proof agreement" in form


def test_readme_routes_operators_to_the_delegation_check():
    readme = (ROOT / "README.md").read_text()

    assert "issues/new?template=delegation-check.yml" in readme
    assert "workflow you still don't trust" in readme
