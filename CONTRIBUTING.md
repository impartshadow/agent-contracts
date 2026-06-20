# Contributing

This repo wants small, deterministic contracts for real agent failures.

## Good Contributions

Strong additions usually look like one of these:

- A new `Contract` subclass for a concrete failure mode.
- A failing test that reproduces a bad action before the fix.
- A tighter default pattern with low false-positive risk.
- A framework adapter that keeps the contract gate at the tool boundary.
- Documentation that helps teams deploy contracts without overclaiming security.

## Contract Bar

Before adding a contract, ask:

1. Can the rule run without an LLM call?
2. Is the input available in `ActionContext`?
3. Is the expected decision stable across runs?
4. Is the failure severe or common enough to justify a default guard?
5. Can a test prove both the block and the allowed path?

If the answer is no, it may belong in application policy rather than this
package.

## Pull Request Shape

Keep PRs narrow:

- One failure mode or adapter per PR.
- Add or update tests in `tests/test_contracts.py`.
- Update `README.md` only when the public API or default behavior changes.
- Add docs for deployment guidance in a focused Markdown file.

Run before opening a PR:

```bash
pip install -e ".[dev]"
pytest -q
python examples/demo.py
python examples/tool_router.py
```

## Default Contract Policy

Not every useful contract belongs in `default_contracts()`.

Default contracts should be broadly safe across agent runtimes. Role-specific
rules, organization-specific rules, legal/compliance checks, and business-policy
guards should usually stay opt-in.
