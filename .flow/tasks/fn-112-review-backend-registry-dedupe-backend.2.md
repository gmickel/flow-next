# fn-112-review-backend-registry-dedupe-backend.2 Plan/completion migration + cursor folds + inherited dedupes

## Description
Plan + completion review migration onto the driver, cursor folds, and the two inherited dedupe items.

**Size:** L
**Files:** both flowctl.py copies, tests

### Approach

- Migrate the plan-review and completion-review command families onto cmd_backend_review, including folding cmd_cursor_validate, cmd_cursor_deep_pass, and the 377-line cmd_cursor_completion_review into the shared pipeline like codex/copilot (fn-112 stub item 4).
- Deep-pass confidence-promotion and verdict-recompute math: RELOCATE ONLY, byte-equivalent behavior - fn-113 decides what survives (stub item 5). Do not change thresholds or semantics.
- Inherited item A (fn-110 deferral): review handlers self-write the review status - after a SHIP/NEEDS_WORK verdict parse, the handler updates plan_review_status (and the equivalent impl/completion state fields) directly instead of requiring a separate flowctl call from the skill; fold `review-rounds` reads into the same handler surface. Keep the standalone `spec set-plan-review-status` + `review-rounds` commands working (skills still call them until the skill-prose update in task 4).
- Inherited item B (fn-114 coordination, we land first): extract ONE `stamp_ralph_iteration(receipt)` helper replacing the ~10 identical RALPH_ITERATION stamping blocks; behavior identical.
- Receipts byte-compatible; verdict tag unchanged; fn-90 cap logic untouched.
- Dual-copy mirrored; sync-codex x2; smoke neighboring flags after parser edits. NO git commands.

### Acceptance

- [ ] All 9 original review clones gone; one driver + registry entries; net flowctl.py reduction so far >= 1,500 LOC vs task-1 baseline
- [ ] Deep-pass/validator math byte-equivalent (same inputs -> same receipt mutations; pin with a fixture test if none exists)
- [ ] stamp_ralph_iteration helper: one definition, all stamping sites call it, receipts identical
- [ ] Focused suites green: test_backend_spec.py, test_cursor_review_commands.py, test_review*.py, test_r22_invariant.py
- [ ] Both copies byte-identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
