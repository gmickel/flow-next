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
Plan + completion review migration complete: all 9 review commands are thin wrappers over cmd_backend_review; cursor validate/deep-pass/completion folded into the shared pipeline (spawn via registry run_exec, old coerce rule intentionally preserved for session-pass paths). Shared _write_backend_review_receipt with stable key order - verified against ALL SIX pre-refactor plan/completion writers plus the three impl writers (base gated to impl/completion, effort conditional per backend). stamp_ralph_iteration: one def, two call sites (shared writer + triage-skip), replacing ~8 inline blocks (fn-114 coordination satisfied - we landed first). Review handlers self-write plan_review_status/completion_review_status + reviewed_at and surface review_rounds in JSON (fn-110 deferral; additive double-write until task .4 updates skill prose; standalone commands unchanged). Deep-pass math relocate-only: _apply_deep_passes_to_receipt, promote_confidence, parse_deep_findings, merge_deep_findings all byte-identical vs pre-spec baseline. LOC: -1251 cumulative vs the >=1500 acceptance target - MISS by 249, carried to .3 (prompt extraction ~780 closes it; recorded honestly, not waved through). Host review: plan --files error-copy unification accepted (unpinned, longer wording); focused suites green (backend_spec 139, cursor 32, review* 45, r22 38); full parallel suite 83 files / 1832 tests / 0 failures / 82.0s; dual-copy identical; sync-codex x2.
## Evidence
- Commits: dd43795433d3a232d918aa720c44ee1484635151
- Tests: python3 scripts/run_tests_parallel.py (83 files, 1832 tests, 0 failures, 82.0s), receipt key-order parity verified vs all 9 pre-refactor writers, deep-pass 4-function byte-identity vs HEAD~2, focused: backend_spec 139 / cursor_review 32 / review* 45 / r22 38
- PRs: