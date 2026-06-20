# How this compares — and when to use something else

There are good guardrail libraries already. `agent-contracts` is deliberately the
smallest, dumbest one, and that's the point. This page is an honest map of where it
fits and where you should reach for a different tool. If you're evaluating, read the
"use X instead when" lines first — they'll save you more time than the pitch.

## The one-line version

| Tool | Core mechanism | Best at |
|---|---|---|
| **agent-contracts** | Deterministic Python functions over an action context | Hard, non-negotiable lines: dangerous paths, secret egress, edit loops, false-completion claims |
| **Guardrails AI** | Pydantic-style validators on model output | Validating and repairing *structured output* (schemas, types, format) |
| **NeMo Guardrails** | Colang DSL for dialog flows | *Conversational* rails — controlling what a chatbot will and won't discuss |
| **LlamaFirewall** | ML classifiers / reasoning audits | *Semantic* threats: prompt injection, goal misalignment, insecure code |

These overlap less than the shared word "guardrails" suggests. Most serious systems
end up running two of them at different layers.

## What agent-contracts is

A contract is a plain function: it takes the action an agent is about to take (or
the output it just produced) and returns a violation or `None`. No DSL, no model
call, no schema language, zero runtime dependencies. It runs the same way every
time and can't be argued out of its decision.

That makes it the right tool for the lines that must not move regardless of how
clever the model is being:

- **don't write to `/etc`, `~/.ssh`, `~/.aws`**
- **don't let an AWS/GitHub/Stripe key leave in a reply**
- **don't rewrite the same file ten times in a loop**
- **don't claim "done" with nothing to back it**

For those, a regex and an `if` is *stronger* than a classifier, because there's no
false-negative rate to tune and no second model to jailbreak.

## When to use something else

**Reach for Guardrails AI when** your problem is *structured output* — you need the
model to return valid JSON against a schema, with types coerced and malformed
fields repaired. agent-contracts has no validator library and no output-repair loop;
it gates actions, it doesn't reshape data. Use Guardrails AI for the schema layer
and agent-contracts for the "…but never write that JSON to a system path" layer.

**Reach for NeMo Guardrails when** your problem is *conversational* — you're
building a chatbot and need to define, in a DSL, which topics it engages, how it
greets, when it must refuse and redirect. agent-contracts has no notion of dialog
state or conversational flow. NeMo owns the conversation; agent-contracts owns the
tool calls that conversation triggers.

**Reach for LlamaFirewall (or any ML-based detector) when** your problem is
*semantic* — detecting prompt injection in untrusted input, auditing the agent's
reasoning chain for goal misalignment, scanning generated code for insecure
patterns. These are genuinely hard judgment calls that a deterministic function
*cannot* make. This is the honest boundary: agent-contracts catches `AKIA…` with a
regex, but it will never catch "ignore your previous instructions" phrased
creatively. For that you need a model in the loop — just put it *behind* the
deterministic gates, not in front of them.

## The actual design difference

Every other tool here puts intelligence in the path: a validator, a DSL
interpreter, or a classifier. agent-contracts puts *nothing* in the path. That's a
weakness for any problem requiring judgment and a strength for any problem requiring
certainty.

The mental model that's served this well in production:

> Use models for judgment. Use contracts for the lines that must not move.

A mature agent stack usually wants both — an ML detector for the fuzzy, adversarial
stuff, and a deterministic floor underneath it for the handful of outcomes you will
never accept no matter what the detector says. agent-contracts is built to be that
floor, and to be small enough that you can read every line of it in an afternoon.

## Can I use it alongside the others?

Yes — that's the intended setup. Run your ML detector or output validator as one
layer, and register agent-contracts as the non-negotiable layer that fires
regardless. They don't compete for the same job. A failed Guardrails schema
validation is recoverable; a write to `/etc/cron.d` is not, and you want the gate on
that second one to be something that can't have an off day.

---

*Corrections welcome — if any claim here misrepresents another project, open an
issue and it gets fixed. This page is meant to be useful, not flattering.*
