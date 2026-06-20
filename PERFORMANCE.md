# Performance

`agent-contracts` is designed to run at every side-effect boundary. The default
contracts are plain Python checks: string scans, path normalization, regexes, and
small list iteration. There is no model call and no network call in the gate.

Run the local benchmark:

```bash
python examples/benchmark.py --iterations 10000
```

The benchmark runs three checks per iteration:

1. A clean file write through `check_pre`.
2. A blocked shell command through `check_pre`.
3. An unsupported completion claim through `check_post`.

Use the number as an order-of-magnitude smoke test, not a universal guarantee.
Your own custom contracts can be slower if they do disk, network, database, or
large-text work. Keep production contracts deterministic and local when the gate
sits in front of every tool call.

Production rule of thumb:

- Fast path: pure string/path/metadata checks.
- Acceptable path: bounded file metadata checks.
- Avoid in the gate: LLM calls, web fetches, unbounded directory walks, database
  queries without strict timeout and scope.
