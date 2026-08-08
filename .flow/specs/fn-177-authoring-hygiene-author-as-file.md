# Overview

Three small prose disciplines from the flow-efficiency replay campaign that each earned a measured or defect-class-backed place, none of which claims speed: author-as-file (-13% cost in both A/B pairs), the examples-are-exhaustive contract clause (the defect class caught twice - SCB dbm-ck2 and fn-93's optional-field deviation), and tiered test runs (36 pytest invocations per checkpoint measured, 54% redundant full-suite re-runs at 3x targeted cost).

**Evidence standing: validated in the flow-efficiency replay campaign (results 06 §4, 05). No new evals. Tested wording exists in worktree commits `c354e78f` (author-as-file) and `570b2fa7` (tiered testing) on `replay/wt/flow-next-bundle`.**

## Goal & Context

Land the three as one hygiene pass: cheaper runs (fewer steps, fewer cache reads), Edit-able planning artifacts instead of re-emitted heredocs, one fewer contract-deviation class, and fewer redundant full-suite runs in autonomous loops - with the full-suite gates untouched.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_dogfood_template_parity test_template_canonical test_review_prompt_constraints -q
./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short   # idempotent (2nd run = no diff)
```

## Architecture & Data Models

Prose-only. Three independent edits (both transplant commits verified to apply cleanly on current main, post-fn-174):

1. **Author-as-file** (`plugins/flow-next/skills/flow-next-plan/steps.md`, tested in `c354e78f`): documents composed with the Write tool at a literal path, revised with Edit - never inside a bash heredoc (heredocs stay legal for short transient payloads ~10 lines or less). Kills the same-block heredoc rule and the re-emission channel. **One correction to the tested wording:** its Route A line invokes `flowctl spec cat <id> --plan`, a verb that does not exist - substitute `"$FLOWCTL" cat <id> >` (the real spec-body dump) at transplant; everything else lands verbatim.
2. **Examples-are-exhaustive** (`plugins/flow-next/templates/spec.md`): no tested commit - author fresh per the spec: when a spec shows an output/event/API shape, the fields shown ARE the contract; implementations must not add fields to a shown shape; if a field is intended, show it. NO length/byte budget anywhere in the block (that half was measured ignored 3x and is dropped). Lands as a short comment block beside the existing SCOPE DISCIPLINE comment.
3. **Tiered test runs** (`plugins/flow-next/agents/worker.md`, tested in `570b2fa7`): two bullets in the Rules list - test-mass discipline (one focused test per AC/error case, table-driven over copy-paste, no re-testing covered branches) and tiered runs (focused tests while iterating; FULL suite exactly at the gates that already require it: pre-edit baseline, pre-review, pre-commit).

Mirrors and copies: sync-codex.sh regenerates `codex/skills/flow-next-plan/steps.md`, `codex/templates/spec.md`, `codex/agents/worker.toml`. `.flow/templates/spec.md` refreshed to match the bundled template (test_dogfood_template_parity enforces). None of the three files is hash-pinned. NOTE: the codex sync transform dedents prose continuation lines by one space - acceptable for these files (no byte-parity requirement; only the four extracted review prompts are byte-pinned).

## Edge Cases & Constraints

- The full-suite gates are the impl-review Tests criterion's foundation and the regression-suite intervention itself - untouched by construction; only mid-loop redundancy changes. R3's one real error surface: any weakening of the three gate mentions fails review.
- Author-as-file transient paths are literal and unique per document (path-persistence rule already in the skill); files deleted only after the artifact is finalized.
- steps.md now carries fn-174's Step 2 scope-minimality block - disjoint region (Step 5), verified clean apply.
- worker.md now carries fn-174's YAGNI bullet - 570b2fa7 inserts after the "Required tests cover..." rule, verified clean apply.

## Acceptance Criteria

- **R1:** Heredoc composition of documents is gone from the plan skill; Write/Edit path present per `c354e78f` (with the phantom `spec cat --plan` corrected to `cat`); ~10-line heredoc exception stated. Errors: none beyond prose.
- **R2:** Template carries examples-are-exhaustive; no length/byte budget anywhere in the block. Errors: none.
- **R3:** Worker rules carry tiered runs + test-mass discipline per `570b2fa7`; baseline/pre-review/pre-commit full-suite gates textually intact. Errors: any weakening of the three gates fails review - the one real error surface here.
- **R4:** Mirrors regenerated (idempotent); CHANGELOG Unreleased entry with cost/quality framing only - NO speed claims (falsified). Docs-site rides the batched release. Errors: parity red blocks merge.

## Boundaries

- No speed claims anywhere (falsified: -9.9% then +9.2% tokens across pairs).
- No spec/task length budgets (rejected lever).
- No changes to gate cadence, review content, or flowctl.

## Strategy Alignment

Active tracks served by this plan:
- **Self-improving through normal work** - replay-campaign findings folded into pipeline prose.
- **Cross-platform parity** - mirrors regenerated with the canonical change.

## Decision Context

Bundled as one spec because all three are small, share the same evidence base and the same "hygiene, not speed" framing, and touch disjoint files - splitting them would triple ceremony for no isolation benefit (the campaign already isolated their effects). Author-as-file survives despite the falsified speed claim because its measured value is cost and revisability, and its quality reviews were split-neutral across two items. Corrected rather than transplanted verbatim: the `spec cat --plan` phantom verb (prose must not instruct a command that does not exist).

## Early proof point

Task fn-177.1 validates the core approach (both tested commits apply cleanly and the fresh examples-are-exhaustive block reads as contract language, not budget language). If the worker.md gate wording drifts, stop before mirrors.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Author-as-file in plan skill | fn-177.1 | - |
| R2  | Examples-are-exhaustive in template | fn-177.1 | - |
| R3  | Tiered runs + test-mass in worker rules, gates intact | fn-177.1 | - |
| R4  | Mirrors + CHANGELOG | fn-177.1 (mirrors), fn-177.2 (CHANGELOG) | - |
