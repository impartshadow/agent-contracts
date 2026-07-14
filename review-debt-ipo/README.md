# Review Debt IPO

This action turns review debt from a private complaint into public work supply. It scans explicit declarations such as “human must approve” or “manual verification,” fingerprints the current checkpoint set, and opens one deduplicated issue where agents must compete with runnable deletion proof.

```yaml
name: Review Debt IPO
on:
  workflow_dispatch:
  push:
    branches: [main]
permissions:
  contents: read
  issues: write
jobs:
  float-review-debt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: impartshadow/agent-contracts/review-debt-ipo@main
```

Add a `review-debt` label once. Each changed checkpoint set creates a new prospectus; unchanged debt never creates duplicate issues. Repositories control whether a proof actually earns deletion.
