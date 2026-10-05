# fn-279 Agentic review through the orchestration rules, standing criteria on the default route

## Conversation Evidence

- "analyse in depth if we can rip out the review.backend ..."
- "this should be a followup probably ... 7.1 or 8.0 later ... deprecate/close the old spec ... write a new one"
- "in terms of the review.backend stuff, we would then use the agentic rules that we already have for orchestration?"
- On the stall guard: option 1 was the lean (review the new fix first, escalate only on a third consecutive `not-fixed`).
- On standing criteria: "yes put this in our follow up spec, fits well into the review backend stuff, will need to measure that it doesnt worsen wall-clock or performance, outcome"

## Goal & Context

7.0 made review lighter in prose: review by risk, one scoped re-review when attended, a loop to SHIP when unattended. The machinery underneath did not change. Every review still goes through `review.backend`, per-backend review workflows and a large block of flowctl review code (about 15.7k lines at the 7.0 analysis, about 40k words across the three review skills, 20-25k test lines). The orchestration block in the project instruction file already routes other work to other models and harnesses through `flowctl usage` and its bridge recipes, so review can run the same way: the agent renders the prompt, dispatches a read-only reviewer from the routing block's reviewer tier, and keeps a small record. [paraphrase]

Two review gaps belong to the same change. The stall guard can refuse a round before a committed fix is reviewed, and plan and completion review have no author override when they run unattended. [paraphrase] Standing criteria in `.flow/criteria.md` are judged only by completion review, which the default single-task inline route skips, so they are never checked on the default route. [paraphrase]

The maintainer deferred this out of 7.0 because it grew too big; it runs after 7.0 ships, as 7.1 or 8.0, and every step is measured with the fn-271 harness against 7.0.0. [paraphrase]

## Architecture & Data Models

- **Review dispatch becomes agentic.** The agent renders the review prompt with the existing stateless prompt renderer, dispatches the reviewer named by the routing block's reviewer tier through the documented read-only bridges (or a read-only host subagent), merges draws (the worst draw's verdict wins; failed draws do not vote), fixes, and resumes the same reviewer session for the one scoped re-review with the declined-finding lines and the fix-commit range. [inferred]
- **A small review record replaces the ledger.** One record per review scope holds the reviewer, model, session id, reviewed head, round, the path of the raw reviewer output saved unedited, its hash, and the verdict. [inferred]
- **State that stays.** Spec-level plan and completion review status fields and their setters (read by `flow --auto`, tracker status sync and an external orchestrator), the per-spec and per-task review selection as plain data, and the review prompt templates with the prompt renderer. [inferred]
- **State that goes.** Backend review verbs, fan-out and finalize, review routing, round ledgers and journals, triage-skip, the deep, validate and walkthrough passes, the backend registry, the managed-execution provider, and the `review.backend` and `review.maxIterations` config keys (retired through the existing removed-config-keys advisory). [inferred]
- **Standing criteria reach the default route.** The single-task inline path hands the repository's standing criteria to the reviewer it already runs, so no extra review is added. [paraphrase]

## API Contracts

- Setup asks whether you want cross-model reviews and writes the reviewer line plus a fail-closed review line into the orchestration block (commented by default), instead of a config key. [paraphrase]
- A config that still sets a retired review key keeps working: flowctl ignores the key and prints a one-line note naming what replaces it. [inferred]
- The spec-level review status values and the verdict lines drivers read (`SHIP`, `NEEDS_WORK`, `ESCALATE:`, `OVERRIDDEN:`) keep their names. [inferred]

## Edge Cases & Constraints

- Review fails closed: when the named reviewer cannot run, the run says so and stops that review; it never substitutes another reviewer or the author. This overrides the routing block's general "never fails closed" rule for the review line only. [inferred]
- The reviewer is read-only on every backend; no draw may leave changes in the checkout. [inferred]
- The verdict stays the reviewer's: the reported verdict must equal the last verdict in the saved raw output. [inferred]
- CLI quirks the flowctl runners handled move into bridge prose: stdin hangs, resume flags and model pinning on resume, trust prompts, session markers, the model-unavailable fallback, Windows sandboxing. [inferred]
- An external orchestrator that calls flowctl's completion review directly must move first; plan and completion review keep their current path until it has. [inferred]
- The evidence so far covers one harness (Claude Code) and one implementing model. [inferred]

## Acceptance Criteria

- **R1:** Implementation review runs agentically end to end (render, dispatch through the routing block's reviewer tier, merge, fix, one resumed scoped re-review, record) with no backend review verb. Errors: reviewer unavailable or bad model id → the run names the reviewer and stops that review, no substitution; transport failure mid-review → the draw fails and does not vote; a session killed mid-loop resumes from the record without repeating a finished round. [paraphrase]
- **R2:** Each review writes one record per scope with reviewer, model, session id, reviewed head, round, raw-output path, raw-output hash and verdict, and the reported verdict equals the last verdict in the raw output in every measured draw. Errors: missing or unparsable raw output → no verdict is recorded and the review reports the failure. [inferred]
- **R3:** Unattended runs still stop: a bounded round count from the record ends a loop that never reaches SHIP with an `ESCALATE:` line, checked with a stub reviewer that never returns SHIP. Errors: a record written by an older round with a different reviewed head → the round count continues rather than resetting. [inferred]
- **R4:** The stall check reviews a new fix before it escalates: it stops only after the reviewer marks the same finding `not-fixed` in three consecutive rounds, and never refuses a round whose committed fix has not yet been reviewed. Errors: no error surface beyond R3's stop. [paraphrase]
- **R5:** Plan review and completion review, when unattended, accept the author override on the same terms as implementation review (hardening, scope creep and pre-existing findings below Major, recorded with an `OVERRIDDEN:` line), and the spec-level review status records the override so `flow --auto` can advance. Errors: an override over a finding that shows a stated requirement broken is refused. [paraphrase]
- **R6:** On the single-task inline route, the reviewer that already runs also judges the repository's standing criteria, and a violated criterion is a finding like any other; no additional review dispatch is added. Errors: no standing-criteria file → the review runs as before with no note. [paraphrase]
- **R7:** `review.backend` and `review.maxIterations` are retired with a one-line advisory, setup's review question writes the orchestration block instead, and the removed flowctl review code, skill text and tests are deleted in the same change that makes them unnecessary. Errors: a config still setting either key → flowctl ignores it and prints the advisory, never an error. [inferred]
- **R8:** Measured with the fn-271 harness against 7.0.0 on at least cases 2 and 4, attended and `--auto`, at least 3 draws each: no hidden check that passes on every 7.0.0 draw fails on any new draw, the case-4 mirror probe passes on every draw, zero reviewer writes, and wall-clock, cost and tokens, stops and judge score are no worse than 7.0.0. R6 is measured the same way on a single-task case carrying a standing criterion. Errors: a draw that regresses any of these blocks the change until explained or fixed. [paraphrase]

## Boundaries

- Review stays cross-model and independent; this changes how it is dispatched, not whether it happens or who decides the verdict. [inferred]
- The review prompt templates and the axis lenses are kept as they are. [inferred]
- Plan and completion review move only after the external orchestrator no longer calls flowctl's completion review. [inferred]
- No new standing-criteria format, and no separate standing-criteria review stage. [paraphrase]

## Decision Context

- **Parked (maintainer, 2026-10-04):** 8.0.0 keeps the deterministic flowctl review path and `review.backend`; agentic dispatch is parked over speed, flakiness across harnesses and breakage. The uniform panel, standing criteria on the single-task route (R6) and the stall-check fix (R4) move to fn-281 on the existing path; R5 (author override for unattended plan and completion review) is not taken. Revisit only with evidence that prose dispatch is as fast and reliable on every harness.
- **8.0.0 migration line (maintainer, 2026-10-03):** 7.1.0 announced `review.backend` as deprecated for 8.0.0. When it goes, `/flow-next:flow` needs a one-line hint that helps a project still setting `review.backend` (or `rp`) move its reviewer into the model-routing block.
This deliberately reverses flow-98's decision to keep `review.backend` as a deterministic carve-out, now that the orchestration block and its bridges drive other harnesses reliably. It supersedes fn-112 (backend registry dedupe) as a plan: that spec consolidated the backends, this one removes them. fn-240's constraint holds: reviewer choice stays separate from whether a review runs, and review fails closed. [paraphrase] What is given up is tool enforcement of the round cap, the transport circuit breaker, the unchanged-artifact stop, round refunds and crash replay; they become rules the agent follows plus the record file, which is auditable rather than enforced, the level host review has today. [inferred] Handing the standing criteria to the reviewer that already runs was chosen over adding a completion review to the single-task route because it adds no dispatch and no wall-clock. [paraphrase] The full analysis and the stall-guard history live in the fn-271 study record. [inferred] Before planning, read that record's "7.1 candidates" list (the maintainer's fn-271 REPORT): it names the items 7.0 left for 7.1, those in this spec and those that need their own, each with the measurement it needs. [paraphrase]
