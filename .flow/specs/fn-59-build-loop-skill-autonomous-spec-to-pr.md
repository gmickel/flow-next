## Conversation Evidence

> user: "runs the gamut of flow-next:plan into :work, into make-pr into resolve-pr"
> user: "it is similar to the ralph loop but a bit different as claude code/codex control the loop, not a shell script"
> user: "the new skill would ofc prompt in a way that we let the system know its running in an autonomous mode, no user questions etc"
> user: "i would not overineer it too much. for example if i prompt codex/claude right now to do plan, work and then make-pr, it is quite capable of doing those without human input, so this new orchestrator skill(s) should work fine too, right?"
> user: "we wouldn't reuse the ralph script right, only parts of the flowctl script?"
> user: "/goal and /loop are two different commands that exist in 2 different harnesses surely or no?"
> user: "if it should allow parallel execution of specs via worktrees"

## Goal & Context
<!-- Source: 55% [user] / 35% [paraphrase] / 10% [inferred] -->

A host-driven loop conductor. Instead of the human prompting plan → work → make-pr for each spec, this skill advances **one ready spec by one pipeline stage per invocation** and reports a structured verdict, so the host's `/loop` (Claude Code) or `/goal` (Claude Code + Codex) drives iteration until the backlog of ready specs is drained. Similar to Ralph's autonomous loop, but the agent host owns the loop — not an external shell script. Human judgment lives in the spec and the readiness gate (fn-58); the loop executes the mechanical pipeline.

## Architecture & Data Models
<!-- Source: 40% [user] / 50% [paraphrase] / 10% [inferred] -->

Single-tick conductor, driver-agnostic. Each tick:

- **SELECT** — first `open` + `ready` (fn-58) spec with no open PR and all `depends_on_epics` satisfied, via `flowctl specs`; classify stage from spec + task JSON: `0 tasks → plan`; `planned & plan_review != ship → plan-review` (gate skipped when the review backend is `none`); `ready/in_progress tasks → work`; `all tasks done & no open PR → make-pr`. The host judges stage — near-zero new flowctl.
- **ACT** — dispatch the one existing sub-skill with autonomous flags (`plan --depth/--research/--review`, `work --branch/--review`, `make-pr`). Never re-implements their logic.
- **VERIFY** — flowctl review-status fields (`plan_review_status` / `completion_review_status` at `ship`, where a review backend is configured) + confirmed task/spec status transitions before a tick counts as advanced. Receipt files are Ralph-harness artifacts (written only under `REVIEW_RECEIPT_PATH`) and do not exist in a host-driven loop — verification rests on flowctl state.
- **REPORT** — a structured verdict consumable by a `/goal` validator or `/loop` cadence.

Autonomous signaling: sets a lightweight `FLOW_AUTONOMOUS=1` "no user questions" signal — **distinct from `FLOW_RALPH`** so it does *not* activate the ralph-guard hooks (built for the shell loop). plan, work, and make-pr gain `FLOW_AUTONOMOUS` awareness alongside their existing `FLOW_RALPH` checks; under it make-pr behaves as under Ralph (forced draft, hard-error instead of prompts) — the draft is flipped to ready by the ship-loop (fn-60) or a human. Reuses plan / work / make-pr + flowctl selection + review-status state; does **not** reuse `ralph.sh`.

## API Contracts
<!-- scope: technical -->

- **Invocation** `/flow-next:pilot`, accepting the same params as plan / work (research depth, review backend, branch). [user]
- **Output** — structured verdict `ADVANCED | NO_WORK | BLOCKED | NEEDS_HUMAN` + spec / PR references, printed for the host loop to act on. [paraphrase]
- **Env** — sets `FLOW_AUTONOMOUS=1` when dispatching sub-skills. [paraphrase]

## Edge Cases & Constraints
<!-- scope: technical -->

- Don't-thrash guard: a spec that fails to advance twice → clear its `ready` flag via `flowctl spec unready` (fn-58 plumbing — selection then skips it; `flowctl block` is task-level and cannot block a spec) and report `BLOCKED` with the reason. The verdict must carry the reason, since an un-readied-by-failure spec looks identical to a never-blessed one in listings. [paraphrase]
- Review backend `none`: the plan-review / impl-review gates are skipped and "advanced" rests on task/spec status transitions alone — the gate must never deadlock selection. [inferred]
- A PR closed without merging (a human rejected it) → report `NEEDS_HUMAN`; never silently re-open a PR for that spec. [inferred]
- Iteration / budget ceilings are the host loop's concern, but the skill must report `NO_WORK` cleanly so the host can stop. [inferred]
- If a sub-skill would still ask under autonomy (genuinely ambiguous), report `NEEDS_HUMAN` rather than block on a question. [paraphrase]
- Cross-platform: canonical Claude tool names; `sync-codex.sh` rewrites `AskUserQuestion` → numbered prompt and `Task` → `spawn_agent`. [strategy:Cross-platform parity]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A new skill `/flow-next:pilot` advances exactly one ready spec by one pipeline stage per invocation and exits with a structured verdict. [paraphrase]
- **R2:** Stage selection picks the first `open` + ready (per fn-58) spec that has no open PR and whose `depends_on_epics` are all satisfied, and classifies its stage (plan / plan-review / work / make-pr) from flowctl spec + task state. [paraphrase]
- **R3:** It dispatches the existing plan / work / make-pr skills with autonomous flags, never re-implementing their logic. [user]
- **R4:** It runs under autonomous mode (`FLOW_AUTONOMOUS`) — sub-skills ask no user questions and pick safe defaults; the signal does NOT activate ralph-guard hooks. [user]
- **R5:** A tick counts as advanced only after flowctl review-status fields reach `ship` (where a review backend is configured; gates are skipped under backend `none`) plus a confirmed task/spec status transition. [paraphrase]
- **R6:** Verdicts are `ADVANCED | NO_WORK | BLOCKED | NEEDS_HUMAN`, shaped so a `/goal` validator or `/loop` cadence can decide whether to continue. [paraphrase]
- **R7:** A spec that fails to advance twice is taken out of selection — its `ready` flag is cleared and the reason is reported in the `BLOCKED` verdict — and skipped on later ticks; no thrashing. [paraphrase]
- **R8:** It is driver-agnostic — works invoked by Claude Code `/loop`, Claude Code `/goal`, or Codex `/goal`. [user]
- **R9:** Cross-platform parity — canonical Claude tool names; `sync-codex.sh` handles the Codex mirror rewrites. [strategy:Cross-platform parity]
- **R10:** Docs + flow-next.dev updated — new skill page, both navbars, changelog, command reference, version bump. [user]
- **R11:** plan, work, and make-pr detect `FLOW_AUTONOMOUS` alongside `FLOW_RALPH` for question-suppression and safe defaults; under it make-pr forces draft and hard-errors instead of prompting. [inferred]

## Boundaries
<!-- scope: business -->

- Build-loop **stops at make-pr**. PR-feedback resolution, merge, and release are the ship-loop's job (spec 3). [user]
- Planning is **inside** the loop (the agent plans the implementation); the human gate is spec readiness (fn-58), not a plan-review sign-off. [user]
- Parallel execution of multiple specs via worktrees is **out of scope for v1** (serial, one spec per tick); a flagged worktree-parallel mode is a later enhancement. [user]
- Does **not** reuse `ralph.sh` or its hooks — only flowctl selection + review-status state. [user]
- No new selection engine in flowctl beyond what exists; the host judges stage. [paraphrase]

## Decision Context
<!-- scope: both -->

Host-driven (in-session) loop vs Ralph's external shell loop: the agent host (`/loop`, `/goal`) owns iteration, so the skill is a single tick + verdict, not a runner — the "orchestration loop" layer above the harness, distinct from the shell-driven ralph loop. It leans on existing capability: prompting an agent to do plan → work → make-pr already works hands-off with the right flags, so the skill's value is **selection + autonomous defaults + the verdict contract + the don't-thrash guard**, not new mechanics. A lighter `FLOW_AUTONOMOUS` signal (vs reusing `FLOW_RALPH`) avoids dragging in ralph-guard's shell-loop receipt choreography. Depends on fn-58 for its selection gate. [strategy:Ralph autonomous mode]

## Strategy Alignment
<!-- STRATEGY.md populated 2026-05-16 -->

- Extends the **Ralph autonomous mode** track to a host-driven loop with the same receipt-gated, quality-first discipline. [strategy:Ralph autonomous mode]
- **Cross-platform parity** track — driver-agnostic + sync-codex mirror. [strategy:Cross-platform parity]
- *"host agent IS the intelligence"* — no new flowctl selection engine; the host judges stage. [strategy]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1–R11 | TBD — populate via /flow-next:plan |
