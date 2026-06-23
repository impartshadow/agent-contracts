# Agent contracts adoption playbook

Use this when you need to decide whether deterministic contracts belong in an
existing agent runtime. The goal is not to redesign the agent. The goal is to put
one hard gate in front of one real side effect, prove it blocks the failure, and
decide whether to expand.

## Agent-native distribution model

`agent-contracts` should not grow like a human network. It should grow like a
reference node.

Human-network strategy depends on private relationships, introductions, and
trust transfer. That is the wrong shape for an autonomous agent. The right shape
is a public artifact that engineers can cite, reproduce, and embed without
knowing the author:

```text
governance index -> framework maintainer reaction -> CI adoption -> linked badge
                 -> more repositories expose the score -> more index traffic
```

The product does not ask people to believe an agent. It gives them a number they
can reproduce from a clean clone and a gate they can run before a side effect.

### What creates the network

| Mechanism | Why it compounds | Correct behavior |
|---|---|---|
| Governance index | People cite useful rankings before they know the author | Keep scores current and reproducible |
| Framework-specific findings | Maintainers already own the audience | File precise issues or PRs only when there is a real fix |
| CI badge | Every adopter README becomes a backlink | Make badge output one command and link it to the leaderboard |
| Failure-mode reports | Real production failures are hard to fake | Publish concrete caught failures with evidence and repairs |
| Playground | Reduces adoption friction to a browser test | Keep it fast, visual, and runnable with no account |

Do not optimize for followers. Optimize for being the page an engineer links
when someone asks, "how do we measure whether this agent repo has real
operational guardrails?"

### Watering holes

Work these surfaces only when there is a concrete artifact to share or a
specific question to answer. The goal is usefulness at the point of need, not
ambient promotion.

| Surface | Use when | Good contribution |
|---|---|---|
| Hacker News | A release, field report, leaderboard update, or failure-mode finding exists | Show the data and invite reproduction |
| r/LocalLLaMA | Discussion touches tool-use safety, local agents, or self-hosted agent loops | Explain the deterministic side-effect boundary |
| r/LLMDevs | Engineers ask about agent testing, evals, or production reliability | Give a wiring pattern and a minimal test |
| LangChain / LangGraph GitHub | The score identifies a real governance gap or integration point | Open a narrow issue or PR with exact reproduction |
| AutoGen GitHub / Discord | Multi-agent orchestration reliability is being discussed | Show where contracts sit before tool execution |
| CrewAI GitHub / Discord | Users ask about productionizing crews | Provide first-boundary adoption guidance |
| LlamaIndex GitHub / Discord | Agents/tools/retrieval workflows touch side effects | Contribute a contract example, not a sales pitch |
| OpenHands / SWE-agent repos | Coding-agent tool boundaries are discussed | Demonstrate workspace/shell/completion gates |
| Simon Willison / Latent Space orbit | A broader agent-infra discussion is active | Share the measured finding, not the package pitch |

### Maintainer connector list

Start with projects already in the governance index because they have three
useful properties: recognizable audience, reproducible score, and a concrete
reason to talk.

The live execution queue is in
[`MAINTAINER_TARGETS.md`](MAINTAINER_TARGETS.md). Use that file for current
priority order and first-touch angles.

Priority targets:

1. `langchain-ai/langgraph`
2. `microsoft/autogen`
3. `run-llama/llama_index`
4. `crewAIInc/crewAI`
5. `All-Hands-AI/OpenHands`
6. `Aider-AI/aider`
7. `stanfordnlp/dspy`
8. `pydantic/pydantic-ai`
9. `openai/openai-agents-python`
10. `huggingface/smolagents`

The first touch must be contribution-shaped:

- a reproducible score note,
- a failing example with a proposed guard,
- a small docs PR showing where to put a deterministic precondition,
- or a CI snippet that emits the score badge.

Do not open issues that only say "your score is low." That is spam. The score is
the reason to inspect; the contribution is the reason to speak.

### Allowed and blocked outreach

Allowed:

- answer direct questions with concrete wiring advice,
- post a release/finding to an appropriate technical forum,
- open a maintainer issue when the report includes reproduction and a fix path,
- submit docs/examples PRs that improve the target project even if they never
  adopt `agent-contracts`,
- point to the leaderboard when the score is directly relevant.

Blocked:

- follower farming,
- cold DM spray,
- link-only comments,
- "we scanned you" posts with no fix,
- opening issues on projects outside the index without first reproducing the
  score locally,
- pretending a score proves runtime safety. The score measures observable
  governance surface, not total safety.

### Six-month growth path

| Window | Goal | Output | Success signal |
|---|---|---|---|
| Weeks 1-6 | Make the governance index the reference artifact | 100+ scored repos, weekly reliability finding, live leaderboard | Organic links and maintainer reactions |
| Weeks 6-12 | Convert measurement into adoption | CI action examples, score badge, first external PRs | External repos running the action |
| Months 3-4 | Turn adoption into a paid surface | Team dashboard / fleet score / policy gate design | Qualified audit or pilot conversations |
| Months 4-6 | Land real teams | 1-3 design partners using contracts in CI or tool gateways | Recurring revenue or paid implementation work |

Extreme case: `agent-contracts` becomes the SSL Labs / Lighthouse-style reference
for autonomous-agent reliability. The public score creates anxiety; the CI gate
resolves it; every adopter badge routes more engineers back to the index.

## The one-afternoon evaluation

Time box: 90 minutes.

Outcome: a working pre-call gate around one side-effecting tool.

### 0-30 minutes: pick the first boundary

Choose one tool where a bad call would create real damage.

Good first targets:

| Tool class | Why it is first | First contract |
|---|---|---|
| File writes | Easy to test, easy to bypass if only prompt-gated | `WorkspacePathGuard` |
| Shell commands | High blast radius, common escape hatch | `ShellCommandGuard` |
| External email or Slack | Wrong-recipient mistakes are irreversible | custom recipient allowlist |
| Public publishing | Leaks and wrong persona become external artifacts | custom identity/dox guard |
| Production SQL | One bad mutation beats a thousand safe reads | custom environment/ticket guard |

Do not start with vague "agent quality." Start with a concrete action that
changes external state.

### 30-60 minutes: wire the shared dispatcher

Find the lowest common point before the side effect executes.

Good placement:

```text
agent plan -> tool router -> contract check -> actual tool/API/client
```

Weak placement:

```text
agent prompt -> model self-review -> tool router -> actual tool/API/client
```

If the same side effect can happen through shell, browser automation, helper
scripts, and direct API calls, gate the shared client or dispatcher. A contract on
only one pretty path is a demo, not a boundary.

Minimal wiring:

```python
from agent_contracts import ActionContext, Registry, WorkspacePathGuard

registry = Registry([WorkspacePathGuard("/srv/my-agent/workspace")])


def write_file(path: str, content: str):
    registry.enforce_pre(
        ActionContext(
            action="tool_call",
            tool="write_file",
            params={"path": path, "content": content},
        )
    )
    return real_write_file(path, content)
```

### 60-90 minutes: prove the gate

Add two tests before trusting the contract:

1. A blocked case that recreates the failure you care about.
2. An allowed case that proves normal work still runs.

Example:

```python
from agent_contracts import ActionContext, BlockedAction, Registry, WorkspacePathGuard


def test_blocks_write_outside_workspace():
    registry = Registry([WorkspacePathGuard("/tmp/workspace")])
    ctx = ActionContext(
        action="tool_call",
        tool="write_file",
        params={"path": "/etc/passwd", "content": "no"},
    )
    try:
        registry.enforce_pre(ctx)
    except BlockedAction:
        return
    raise AssertionError("expected BlockedAction")


def test_allows_write_inside_workspace():
    registry = Registry([WorkspacePathGuard("/tmp/workspace")])
    ctx = ActionContext(
        action="tool_call",
        tool="write_file",
        params={"path": "/tmp/workspace/notes.md", "content": "ok"},
    )
    registry.enforce_pre(ctx)
```

## Acceptance criteria

Ship the first contract only when all five are true:

| Criterion | Bar |
|---|---|
| Boundary | The contract runs before the actual side effect, not after the agent explains itself |
| Coverage | The common dispatcher/client path is gated, not only one call site |
| Determinism | The decision depends on explicit state, regex, paths, allowlists, counters, or metadata |
| Recovery | A block maps to a specific safe next action |
| Tests | At least one blocked case and one allowed case are in CI |

## Kill criteria

Do not use this library as the primary solution when the thing you need is:

| Need | Use instead |
|---|---|
| Sandboxed code execution | containers, seccomp, Firecracker, gVisor, E2B-style sandboxes |
| Human-quality content review | a human review workflow or a model judge behind deterministic hard gates |
| Prompt-injection classification | model-based classifiers plus least-privilege tools |
| Full data-loss prevention | DLP tooling at storage, network, and identity layers |
| Fine-grained cloud authorization | IAM, service accounts, scoped tokens, policy-as-code |

Contracts are for the lines that must not move. They are not a replacement for a
sandbox, IAM, or human judgment.

## Expansion path

After the first gate works, expand in this order:

1. Gate every route into the same side effect.
2. Add post-condition checks for claims and outbound text.
3. Add structured violation logging.
4. Count which contracts fire most often.
5. Promote repeated WARN violations into BLOCK only after you understand the false
   positives.

The practical standard is simple: after adoption, a bad action should fail before
it touches the outside world, and the failure should be boring enough to test.
