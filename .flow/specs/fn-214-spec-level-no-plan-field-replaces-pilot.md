# Spec-level no_plan field replaces pilot --no-plan flag

## Conversation Evidence

> user (turn 1): "The pilot thing makes no sense. Like pilot --no-plan Currently only does specs with zero tasks, right? Is that correct? Can you check the implementation?"
> user (turn 2): "my point is that pilot is meant for autonomous automation, right? And it works based on readiness, but we don't have a readiness for something that has no plan."
> user (turn 2): "So we need both a flag that is spec readiness, which we already have, right, and I think that works with or without tracker sync, right? Confirm that for me."
> user (turn 2): "But we also need something that is skip plan or no plan field true that it can be set at capture time or manually."
> user (turn 2): "We need to do this in a way that is backwards compatible and will just work for people with minimal edits."
> user (turn 3): "Surely we can just drop the pilot flag, no plan, and pilot just builds everything, it is marked as ready and if something is marked and ready and also has the no plan ball then that is also ready and will be done in the pilot thing."
> user (turn 4): "Yeah, we can refuse it at set time. And if something is marked incorrectly as no plan, but has tasks, then the agent can probably deal with it during pilot, right, or work."
> user (turn 5): "just capture it as a spec."

## Goal & Context

<!-- Source-tag breakdown: 60% [user], 30% [paraphrase], 10% [inferred] -->

Pilot is the autonomous build-loop conductor: it selects work by spec readiness (the human-owned `ready` flag, which works identically with or without a tracker configured — `tracker.readyState` is an optional projection onto the same field). But the no-plan route — a trivially small spec that should skip planning and go straight to work — currently has no per-spec signal. It exists only as pilot's `--no-plan` invocation flag, which applies as a blanket to whatever spec the tick selects. In an autonomous loop that is the wrong grain: one flag governs a heterogeneous backlog, and there is no way to mark an individual spec as "ready, and too small to plan."

This spec moves the no-plan decision onto the spec itself as a durable `no_plan` field, set at capture time or manually, and removes pilot's blanket flag. A spec that is marked ready and carries `no_plan` is built by pilot directly through the work stage's existing no-plan route. The change must be backwards compatible and just work for existing users with minimal edits.

## Architecture & Data Models

<!-- Source-tag breakdown: 50% [paraphrase], 50% [inferred] -->

The `no_plan` boolean joins the spec record alongside the existing `ready` flag, following the same pattern (absent key reads false). flowctl owns the field write with set-time validation; pilot and work read it from the spec JSON they already load. The signal flows one way: capture or a manual verb sets it, pilot's classification consumes it, work's existing no-plan route executes it (minting the one implicit task). No new subsystem; the routing decision moves from invocation state to item state.

## API Contracts

- New flowctl verb to set/unset the field (shape per plan; mirrors the `spec ready`/`unready` pattern). Setting it on a spec that already has tasks is refused at set time. [paraphrase]
- The field is exposed on the spec JSON read surfaces pilot and work already consume (e.g. `ready --all`, `show --json`), absent key = false. [paraphrase]
- Pilot's argument parser no longer accepts `--no-plan`; an invocation still passing it gets the existing unknown-flag one-line "ignored" notice and the tick proceeds normally. [paraphrase]

## Edge Cases & Constraints

- **Stale field (marked no_plan but tasks exist):** inert by construction. Pilot's classification is first-match on task count, so the zero-task rows never match and the field is never read; work ignores it with a one-line notice, matching its existing flag semantics. The agent deals with it; no repair machinery. [paraphrase]
- **Backward compatibility:** absent field reads false everywhere — every existing spec, `.flow/` directory, and workflow behaves byte-identically. Zero-task specs without the field still classify as `plan`. [paraphrase]
- **Users still invoking `pilot --no-plan`:** degradation is the visible unknown-flag notice; their zero-task specs route through `plan`, the safe default. [paraphrase]
- **Never inferred:** no autonomous path (pilot, Ralph, capture autofix) ever sets `no_plan` on its own judgment — it is an explicit human instruction, same doctrine as readiness. [paraphrase]

## Acceptance Criteria

- **R1:** A flowctl verb sets/unsets a `no_plan` boolean on a spec, persisted in the spec record and exposed on the JSON read surfaces pilot and work consume; absent key reads false. Errors: unknown spec id → error exit; setting on a spec that already has tasks → refusal with a message naming why; unsetting a never-set spec → idempotent no-op (mirrors `unready`). [paraphrase]
- **R2:** Pilot classifies a ready spec with 0 tasks and `no_plan=true` as the `work` stage dispatched with the no-plan instruction, with no pilot invocation flag involved. A ready zero-task spec without the field classifies as `plan`, unchanged. Errors: field true but tasks exist → zero-task rows don't match, spec flows through the normal pipeline. [paraphrase]
- **R3:** Pilot's `--no-plan` invocation flag is removed from the parser and its forwarded-flag prose deleted; a stray `--no-plan` argument produces the existing one-line unknown-flag notice and the tick proceeds. Errors: no error surface beyond the notice. [paraphrase]
- **R4:** Work honors the spec's `no_plan` field on a zero-task spec as the explicit no-plan instruction (equivalent to today's `--no-plan` flag / stated phrase), including when dispatched by pilot or invoked directly; the explicit flag is retained for direct invocation. Errors: field set but tasks exist → one-line notice, normal task flow (existing flag semantics). [paraphrase]
- **R5:** Capture offers setting `no_plan` at capture time as an explicit opt-in (flag or consent question), never silently inferred; autofix mode requires the explicit flag. Errors: opt-in on a capture whose draft implies multiple tasks → still allowed (spec has no tasks yet; the set-time refusal only guards task presence). [paraphrase]
- **R6:** Docs and mirrors updated in the same change: flowctl reference, pilot/work/capture skill prose, `sync-codex.sh` run twice with a clean mirror diff, and the docs-site downstream per the release workflow. Errors: no error surface beyond the repo's existing guards. [inferred]

## Boundaries

- No tracker mapping for `no_plan` — the field stays flow-local; `tracker.readyState` continues to project only readiness. [inferred]
- No natural-language inference of no-plan anywhere on the autonomous path — flag/field/verb only. [paraphrase]
- No repair or auto-clear machinery for a stale field (e.g. plan clearing it when minting tasks) — staleness is inert; polish like auto-clear is out of scope. [paraphrase]
- No changes to readiness semantics, the strike ledger, or backlog-mode selection — `no_plan` is read only at classification, after selection. [paraphrase]
- No Ralph-specific changes — Ralph benefits through work's field read. [inferred]

## Decision Context

### Motivation

<!-- scope: business -->

Pilot is meant for autonomous automation and works based on readiness, but there is no readiness-shaped signal for "this needs no plan" [user]. The routing decision must live on the item, not the invocation, so a heterogeneous backlog can mix planned and no-plan specs under one loop [paraphrase]. Backwards compatibility with minimal edits for existing users is a hard constraint [user — findable: turn 2].

### Implementation Tradeoffs

<!-- scope: technical -->

- Drop pilot's `--no-plan` flag entirely rather than keeping it as an alias — the field is the single signal; the unknown-flag notice makes removal graceful. [paraphrase]
- Refuse setting `no_plan` on a spec with tasks (set-time validation) rather than allow-and-ignore — cheap validation prevents a lying field; the residual stale case (set while empty, planned later) is inert by construction and the agent deals with it. [paraphrase]
- Rejected: spec-carried state via labels/prose markers — a real field on the spec record follows the proven `ready` pattern and is readable in calls pilot already makes. [paraphrase]

## Requirement coverage

| R-ID | Task |
|---|---|
| R1 | fn-N.M (TBD — populate via /flow-next:plan) |
| R2 | fn-N.M (TBD — populate via /flow-next:plan) |
| R3 | fn-N.M (TBD — populate via /flow-next:plan) |
| R4 | fn-N.M (TBD — populate via /flow-next:plan) |
| R5 | fn-N.M (TBD — populate via /flow-next:plan) |
| R6 | fn-N.M (TBD — populate via /flow-next:plan) |
