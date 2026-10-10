---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-290-host-implementation-reviews-use-the.1 Implement Host implementation reviews use the project's standing review focus

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
impl-review's other-paths.md Step 0 (the argument parse behind the host backend and --deep/--validate) now falls back to the review focus the project's instructions state when the request names none, matching the CLI fast path. The host workflow already passes FOCUS_AREAS to every review-prompt draw and records it on the receipt, so the standing focus now reaches host reviewers and their receipt. Codex mirror regenerated.

Checked: full suite (216 files, 3995 tests, 0 failures); host render fence via `flowctl review-prompt impl ... --focus` shows a Focus Areas section with the focus and none without it; sync-codex --check fresh.

stage: impl-review - ran (model: gpt-6-astra) SHIP, one reviewer, focus "overengineering, slop and YAGNI"

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: a5cb021fb41cc6507e24f8ed8f3f79816dac66f5
- Tests: python3 scripts/run_tests_parallel.py
- PRs: