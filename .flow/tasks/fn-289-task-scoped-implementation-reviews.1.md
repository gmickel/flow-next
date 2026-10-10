---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-289-task-scoped-implementation-reviews.1 Implement Task-scoped implementation reviews carry a review focus

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Task-scoped impl reviews now accept --focus on every route. The task prompt renders the same Focus Areas section standalone reviews use (shared `_review_focus_section`); the fan-out refusal is removed; the single-reviewer route renders the focus it already recorded; review-prompt renders it for host reviews; a re-review adopts the focus from the resolved receipt (explicit, REVIEW_RECEIPT_PATH, or default). A blank focus is no focus. The impl-review skill (and Codex mirror) passes the review focus the project's instructions state; the host receipt template gains an optional `focus` field. CHANGELOG Unreleased updated.

Tests: five focus tests in test_review_fanout.py (four fail on the pre-change code; the re-review test also fails on the first commit); review test files 611/611 green; ruff 0.16.0 clean; sync-codex --check fresh. Real run: `flowctl review-prompt impl fn-289...1 --focus "over-engineering, slop, YAGNI"` renders the section.

stage: impl-review - ran [codex fan-out NEEDS_WORK (3/3 draws, one shared R3 finding: focus read before receipt path resolution) -> fixed in 15595593 -> re-review SHIP] (model: gpt-6-astra)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 9058141c83bc8e8897f0c6bbc00817c9bd4897e6, 155955932b671495b5dd5b2327ff3bcc0f36b8aa
- Tests: python3 scripts/run_tests_parallel.py --pattern 'test_*review*.py'
- PRs: