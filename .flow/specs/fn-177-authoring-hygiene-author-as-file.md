# Overview

Three small prose disciplines from the flow-efficiency replay campaign that each earned a measured or defect-class-backed place, none of which claims speed: author-as-file (−13% cost in both A/B pairs), the examples-are-exhaustive contract clause (the defect class caught twice — SCB dbm-ck2 and fn-93's optional-field deviation), and tiered test runs (36 pytest invocations per checkpoint measured, 54% redundant full-suite re-runs at 3x targeted cost).

**Evidence standing: validated in the flow-efficiency replay campaign (results 06 §4, 05). No new evals. Tested wording exists in worktree commits `c354e78f` (author-as-file) and `570b2fa7` (tiered testing) on `replay/wt/flow-next-bundle`.**

## Goal & Context

Land the three as one hygiene pass: cheaper runs (fewer steps → fewer cache reads), Edit-able planning artifacts instead of re-emitted heredocs, one fewer contract-deviation class, and fewer redundant full-suite runs in autonomous loops — with the full-suite gates untouched.

## Architecture & Data Models

Prose-only. Three independent edits:

1. **Author-as-file** (`skills/flow-next-plan/steps.md`, tested in `c354e78f`): plan.md / tasks.json / any document is composed with the Write tool at a literal path and revised with Edit — never inside a bash heredoc (heredocs stay legal ≤10 lines). Kills the same-block heredoc rule (its "vars die across tool calls" justification dissolves under literal paths) and the re-emission channel (plan.md was measured re-written 7x in one SCB checkpoint).
2. **Examples-are-exhaustive** (`templates/spec.md`): when a spec shows an output/event/API shape, the fields shown ARE the contract — implementations must not add fields to a shown shape; if a field is intended, show it. (The length-budget half of the original template block is explicitly dropped — measured ignored three times.)
3. **Tiered test runs** (`agents/worker.md`, tested in `570b2fa7`): focused tests for the code under change while iterating; the FULL suite exactly at the gates that already require it — pre-edit baseline, pre-review, pre-commit. Plus test-mass discipline: one focused test per AC/error case, table-driven over copy-paste, no re-testing covered branches.

## Edge Cases & Constraints

- The full-suite gates are the impl-review Tests criterion's foundation and the regression-suite intervention itself — they are untouched by construction; only mid-loop redundancy changes.
- Author-as-file transient paths are literal and unique per document (path-persistence rule already in the skill); files deleted only after the artifact is finalized.

## Acceptance Criteria

- **R1:** Heredoc composition of documents is gone from the plan skill; Write/Edit path present per `c354e78f`; ≤10-line heredoc exception stated. Errors: none beyond prose.
- **R2:** Template carries examples-are-exhaustive; no length/byte budget anywhere in the block. Errors: none.
- **R3:** Worker rules carry tiered runs + test-mass discipline per `570b2fa7`; baseline/pre-review/pre-commit full-suite gates textually intact. Errors: any weakening of the three gates fails review — that is the one real error surface here.
- **R4:** Mirrors, docs-site, CHANGELOG (cost/quality framing only — NO speed claims; the campaign falsified those). Errors: parity red blocks merge.

## Boundaries

- No speed claims anywhere (falsified: −9.9% then +9.2% tokens across pairs).
- No spec/task length budgets (rejected lever).
- No changes to gate cadence, review content, or flowctl.

## Decision Context

Bundled as one spec because all three are small, share the same evidence base and the same "hygiene, not speed" framing, and touch disjoint files — splitting them would triple ceremony for no isolation benefit (the campaign already isolated their effects). The one design choice worth recording: author-as-file survives despite the falsified speed claim because its measured value is cost and revisability, and its quality reviews were split-neutral across two items.
