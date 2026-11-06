# No-plan route: refusal, ask, plan-first (gated reference)

> Read from [no-plan-route.md](no-plan-route.md) unless `NO_PLAN=1` is set with no
> contradicting signal, and for § Concurrent mint when the mint's `task create` exits nonzero.

## Autonomous refusal

Under ANY autonomy marker (`FLOW_AUTONOMOUS`, `AUTONOMOUS=1` /
`mode:autonomous` — scan the marker family/namespace, never a fixed two-var list) WITHOUT an explicit no-plan instruction, stop with the typed
report: `NEEDS_HUMAN: spec has no tasks - choose $flow-next-work <spec-id> --no-plan or $flow-next-plan <spec-id>`.
Never ask, never fall through. An explicit no-plan instruction — the flag or stated
intent in the dispatching invocation, or the spec's own `no_plan: true` field (an explicit human write, or the route `flow --auto` records before dispatch, which is how its classification routes here) — is the
only thing that lets an autonomous run take the Direct route; a contradicted signal
(flag or field says direct, prose says plan) is never an explicit no-plan instruction.
A run that asked or continued under autonomy without that instruction has broken this.

## The ask (interactive only)

Read [`plan-vs-no-plan.md`](../../flow-next-flow/references/plan-vs-no-plan.md) and
judge this spec against it; print its `Recommended next:` line in that file's shape,
with the reason. Ordinary implementation decisions may remain with the worker.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

Then ask via `plain-text numbered prompt` — question "This spec has no tasks. How should this run
proceed?" plus the recommendation line, with these two options — and wait for the
answer. Never silently skip the question.

- **Flow-Next work --no-plan (Recommended)** — build the whole spec now as one task, with the same review and QA gates
- **Plan first** — stop; run $flow-next-plan to break the spec into tasks first, then re-run work

A run that continued before the answer arrived has broken this.

## Plan-first answer

Persist this choice with `$FLOWCTL spec clear-no-plan <spec-id> --json`; stop on
failure. Then STOP this run with a one-line pointer: run `$flow-next-plan <spec-id>`, then re-run `$flow-next-work <spec-id>`. Work never invokes plan itself and never chains into it. A run that invoked or chained `/flow-next:plan` has broken this.

## Concurrent mint

`--require-empty-spec` makes the mint
atomic: flowctl refuses (nonzero exit, naming the existing task) when the spec already
has any task, checked under the same lock that allocates ids — so of two concurrent
direct-route runs exactly one mints. The loser STOPS with a typed report naming that
existing task — it never claims, resumes, or dispatches in the same invocation: the
winner is live, and `flowctl start` refuses an `in_progress` task held by this same
actor unless `--reclaim` is passed, which only Phase 1's evidence-checked resume
admission licenses. A LATER re-invocation — after the concurrent run finished or
died — resumes the task through the normal path (task count is 1; a second mint is
unreachable by construction; Phase 1 admits the owner on evidence and 3b claims it
with `--reclaim`): crash-resume stays legal, concurrent double-dispatch does not.
