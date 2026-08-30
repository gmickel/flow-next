---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-212-flowctl-memory-upsert-deterministic.1 Implement flowctl memory upsert - deterministic find-or-create

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Added `flowctl memory upsert` - deterministic find-or-create (exact --title match within --track, byte-for-byte): zero matches create via the existing add path, one match updates in place via add --update (matched entry's own category wins, stale entries matched), 2+ matches fail closed listing ids; over-80 titles rejected (stored titles truncate at 80); scan+decision+write serialized under one cross-process lock; non-JSON output is exactly one Created/Updated line; JSON carries entry_id + action. Collapsed the qa workflow.md 5.5 drift-memo list+jq fold and the features maintain.md bug-filing create-then-fold-then-delete fold to one upsert call each (drift title identity + feature-map-drift tag preserved); docs (flowctl.md, memory-schema.md), CHANGELOG Unreleased entry, new test_memory_upsert suite (10 tests), CLI surface allowlist extended, tracker manifest + codex mirror regenerated.

Note on R5: maintain.md's `feature-map-drift` block is read-only enumeration (memory list), which a write verb cannot replace - its hand-rolled find-or-create fold was the bug-filing block, now on upsert; SKILL.md/maintain.md verb mentions updated for accuracy.

baseline: green (test_memory_core test_memory_marks test_memory_schema, 185 tests OK pre-edit)

stage: impl-review - ran [2 rounds: NEEDS_WORK (4 findings: cross-category match, overlong-title identity, scan/write lock, single-line output) -> all fixed -> SHIP]
## Evidence
- Commits: b19be4c15cc6db8c62d603f9769b7d416cdd038d, 5c302547392fc52a7c7a04abaa01cde5ec559971
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_memory_upsert test_memory_core test_flowctl_surface test_features_skill_contract test_qa_receipt test_tracker_distribution -q (136 tests OK), uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py plugins/flow-next/tests/test_memory_upsert.py, python3 scripts/gen_tracker_manifest.py, ./scripts/sync-codex.sh x2 (idempotent)
- PRs:
stage: plan-sync - skipped(config: planSync.enabled != true)
