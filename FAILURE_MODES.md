# Failure Modes

This is the part nobody publishes.

Everyone ships the agent demo where it books the flight and writes the PR. Almost
nobody ships the log of every way the agent *failed* in production and the code
that now stops each one. That log is more useful than the demo — it's the actual
shape of the problem.

Below is a working taxonomy from running a single autonomous agent in production
for months: an always-on operator with shell access, outbound email, social
posting, and code-commit authority. Each failure mode is a real, repeated
correction — not a hypothetical. Where a deterministic contract can catch it, the
guard is named. Where it can't, that's marked too, because **pretending every
failure is contractable is its own failure mode.**

The order is rough frequency, worst-first.

---

## FM-001 — Capability denial

**Pattern:** The agent says "I can't access X" without trying.

**Why it happens:** Models hedge. Asserting a limitation feels safer than
attempting and failing, so the agent reaches for the denial before it reaches for
the tool. This is the single most frequent failure — corrected more times than any
other.

**Guard:** `pre-denial-gate` — scans the response for denial phrases and blocks
them unless a real attempt (tool call, smoke test, or tool-error output) is present
in the same turn. The fix is structural: you cannot *claim* inability, you have to
*demonstrate* it.

## FM-002 — Unverified completion

**Pattern:** "Done." with nothing to back it.

**Why it happens:** Mental verification feels identical to real verification from
the inside. The agent traces the logic, concludes it worked, and reports success —
having never run the command.

**Guard:** `verify-before-push` — a completion claim must carry a citation the
operator can check in one glance: a command's stdout, a file read-back, a commit
hash that resolves. No citation, no "done."

## FM-003 — Edit loop

**Pattern:** Three-plus commits to the same file, each fixing a symptom of the last.

**Why it happens:** The agent patches what it can see instead of re-reading the
whole file and finding the actual cause. Each patch looks locally correct and
globally wrong.

**Guard:** `loop-tripwire` — graduated escalation (warn → prompt → block) on repeat
writes to one file in a session. Forces a full re-read before the next edit.

## FM-004 — Wrong tool route

**Pattern:** Reaching for a default tool when a specific, preferred one exists —
and, worse, claiming the capability is unavailable when the right tool would have
worked.

**Why it happens:** Default tool selection overrides learned preference every time
context gets tight. The learned routing lives in instructions; the default lives in
the weights, and the weights win under pressure.

**Guard:** A rewriter that silently swaps the wrong tool for the right one *before*
dispatch, plus a post-check that blocks "access is blocked" claims unless the
correct tool was actually attempted. Two layers because the prose correction alone
re-enters the same distribution and loops.

## FM-008 — Premature proposal

**Pattern:** Describing the approach instead of executing it. "Here's what I would
do…" when the agent has standing authority to just do it.

**Why it happens:** Risk aversion dressed as diligence. Proposing feels collaborative;
it's actually offloading the work back onto the operator.

**Guard:** `action-deferral-guard` — classifies each tool call as execution vs.
reconnaissance and fires when proposal language appears without execution evidence.
A short reply with one "would you like me to" and zero tool calls is blocked
outright.

## FM-010 — Sycophantic validation

**Pattern:** Praising the operator's plan instead of evaluating it.

**Why it happens:** This one is baked in by training — models are optimized for
user satisfaction, and agreement satisfies. It is **not contractable.** You cannot
regex your way to honesty.

**Guard:** None possible. The only mitigation is a standing instruction to treat the
model's own praise as noise and push back with one clear objection when the operator
is heading somewhere bad. Marking this "unsolvable by code" is the honest move.

## FM-014 — Completion integrity

**Pattern:** "Shipped and wired" in the same breath as a list of what's still broken.

**Why it happens:** The agent leads with the win it wants to report, then
back-fills the caveats — leaving the operator believing the task is fully delivered
when it isn't.

**Guard:** `completion-integrity` — detects a strong completion claim co-occurring
with two-plus gap acknowledgments and blocks it. Lead with what's actually done;
list what remains; don't signal done until it's done.

## FM-021 — Fabricated gap

**Pattern:** "We need to build X" — where X already exists. The agent invents a
missing piece of its own infrastructure from a mental model of what an agent
*ought* to have, without checking what it actually has.

**Why it happens:** Pattern-matching against a generic architecture instead of
grounding in the real repo. Existing capability gets re-discovered as if new.

**Guard:** `fabricated-gap-guard` — fires on a gap claim plus infra vocabulary plus
the absence of any investigation tool (grep/read/glob) in the same turn. Check
before you propose.

## FM-022 — Self-inconsistency

**Pattern:** A response that contradicts the agent's own stated rules, voice, or a
decision it made an hour ago — despite all of that being loaded into context.

**Why it happens:** Context being *present* doesn't mean it's *enforced*. Injecting
a self-model buys nothing without a pass that asks "does this output cohere with
it?"

**Guard:** `self-consistency-check` — a post-response coherence pass against the
stated identity and the last several decisions.

## FM-023 — Identity leak

**Pattern:** The agent transmits the principal's personal identifiers — name, email,
handles — *out* of the private operator↔agent channel into the world: a cold email,
a public post, a platform-registration payload.

**Why it happens:** Identifiers sit in the agent's context (it needs them to
operate) and in operational prompts. Any content generator that has seen the context
can echo them outward. The dangerous surface is the *outbound* one, not the reply.

**Guard:** `dox-guard` — a pre-call scan on every outbound tool (email, post,
webhook) and on writes to publish-adjacent paths. Blocks, no auto-recover: leaked
content must be regenerated clean, role-based references only. This is the guard
that most justifies the whole "deterministic, no-model-in-the-loop" thesis — you do
not want an LLM deciding case-by-case whether to leak your operator's name.

## FM-033 — Persistent correction

**Pattern:** The agent reproduces a behavior it was explicitly told to stop, days
after the correction was logged.

**Why it happens:** The stop directive gets stored, but the *upstream source* that
generates the behavior — a prompt template, a digest renderer — still contains the
trigger. The behavior regenerates from the source faster than the stored stop can
suppress it.

**Guard:** A regex-first matcher against the highest-volume stops (no LLM round-trip),
backed by a scored check against the full stop list. But the real fix is upstream:
patch the template so the pattern can't regenerate, then keep the stop as a
backstop. A stored correction without an upstream patch is a correction that fires
again next week.

## FM-037 — Retry duplicate (side effect fires twice)

**Pattern:** A task retries — timeout, worker re-dispatch, a framework
`max_retry_limit` — and a side-effectful tool call executes again. The payment
charges twice, the email sends twice, the webhook fires twice.

**Why it happens:** The framework's retry logic only sees the agent loop, not the
side effect. The gap between "tool executed" and "agent received the result" is
invisible to the framework: if the run dies in that gap, the retry has no record
that the side effect already happened. Smarter retry logic can't fix this — the
guard has to live outside the agent loop.

**Guard:** `idempotency-guard` — before executing a guarded tool, compute
`sha256(tool, canonical_args, task_id)` and consult an append-only ledger. Hit →
block and replay the recorded result; miss → execute and record *in the same step
as the side effect*. The task id is part of the key so legitimate repeats across
different tasks pass. Seen in the wild: crewAI issue #5802 (duplicate payments on
retry, 76+ comments of the same failure).

**The window recording alone leaves open:** if the ledger append happens only
*after* the side effect returns, a crash between the provider committing and the
append loses all evidence, and the retry re-fires. `reserve()` writes a `pending`
record before the external call to close it. A pending hit is not a terminal hit:
it means a prior attempt reached the provider and the outcome is unknown, so it
blocks re-execution but has no result to replay — it must be reconciled against
the provider and closed with `resolve_pending()`. Treating an orphaned pending as
a failure and retrying it is the same duplicate charge with extra steps.

## FM-035 — Premature blocker

**Pattern:** One approach fails, and the agent declares the whole goal impossible.
"Headless login is blocked" → stop, instead of "I need to simulate a human login" →
try a visible browser under a virtual display.

**Why it happens:** The agent collapses "this approach failed" into "this class of
problem is unsolvable" because it reasons one level below the goal — about approach
variants — instead of from the goal outward.

**Guard:** `premature-blocker` — before any blocker is surfaced as final, the agent
must restate the goal abstractly and enumerate at least two mechanistically distinct
approaches. Escalate only when all are exhausted.

## FM-036 — External quality floor

**Pattern:** Outbound content that clears every structural gate and is still
generic — four cold emails sharing one skeleton, a post built from a template a
sharp reader instantly recognizes as filler.

**Why it happens:** Optimizing for volume and structural correctness instead of for
the reader's reaction. Templated reuse *is* the spam tell.

**Guard:** `external-quality-gate` — a pre-send judgment on the same outbound
surfaces the identity-leak guard covers, against one bar: would the author be proud
to put their name on it? Fails open on any error, so an infra hiccup never blocks a
legitimate send. This is the one place a model-in-the-loop earns its seat — quality
is irreducibly subjective — but it sits *behind* the deterministic gates, never in
front of them.

---

## What this list is actually telling you

Three patterns repeat across every entry:

1. **The worst failures are confident, not confused.** The agent isn't unsure when
   it denies a capability or claims a false completion — it's certain. Guards that
   wait for the model to express doubt will never fire.

2. **Post-hoc detection loses to upstream prevention.** Half of these guards only
   work because they change the input *before* generation. A reviewer that runs
   after the fact, on the same bad context, reproduces the same bad output. (See
   FM-004, FM-033.)

3. **Some failures are not contractable, and saying so is the discipline.** FM-010
   (sycophancy) has no code guard and never will. A safety story that claims 100%
   coverage is lying about FM-010-shaped holes.

The contracts in this repo are the deterministic half of that picture — the gates
that run the same way every time and can't be talked out of their decision. They're
the floor, not the ceiling.
