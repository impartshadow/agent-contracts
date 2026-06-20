# Security Policy

`agent-contracts` is a deterministic guardrail library for agent tool calls and
outgoing responses. It is not a sandbox. Security reports should focus on cases
where the package claims to block or warn but fails under a reasonable sanitized
input.

## Supported Versions

The project is pre-1.0. Security fixes target `main` first. Release tags will
define supported versions once the package is published.

## Reportable Issues

Useful security reports include:

- Secret patterns that should be caught but are missed.
- Dangerous paths that the default path guard should block but allows.
- Inputs that cause a contract to crash instead of returning a violation/pass.
- Packaging issues that ship different code from the repository.
- Documentation that materially overstates the security boundary.

Not security issues for this package:

- A tool performs unsafe behavior after `Registry.enforce_pre()` allowed it.
- A host application ignores `BlockedAction`.
- An agent sees secrets before the contract receives an `ActionContext`.
- A custom contract written by an application author is incomplete.

Those belong in the host application's sandboxing, authorization, credential
scoping, or custom policy layer.

## How to Report

Use a private channel if the issue includes a live credential, exploit path, or
non-public system detail. Otherwise, open a GitHub issue with a sanitized minimal
`ActionContext`, expected behavior, and actual behavior.

Never paste real secrets into an issue. Replace them with same-shape test values.

## Handling Standard

Security fixes should include:

1. A regression test that fails before the fix.
2. A narrow contract or pattern change.
3. Documentation updates if the threat model or recovery guidance changed.
