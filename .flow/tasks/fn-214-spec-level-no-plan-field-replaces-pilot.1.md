---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-214-spec-level-no-plan-field-replaces-pilot.1 Implement Spec-level no_plan field replaces pilot --no-plan flag

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Spec-level `no_plan` field replaces pilot's --no-plan flag. flowctl gains `spec set-no-plan` / `spec clear-no-plan` mirroring the ready/unready lazy contract (set refused once tasks exist; clear always allowed), with the field exposed on show/specs/list --json and as `noPlan` on `ready --all` rows (R1). Pilot's parser drops --no-plan (stray flag = unknown-flag notice) and its zero-task classification row reads `SPEC_JSON.no_plan`, appending --no-plan to the work dispatch when matched (R2/R3). Work reads the field as the explicit no-plan instruction, flag retained for direct invocation, tasks-present = notice + ignore (R4). Capture takes an explicit exact-token `--no-plan` opt-in (interactive and autofix; never inferred) writing via §5.9b after the spec write (R5). Docs (flowctl.md, pipeline-variations, docs/README, guide), conduct checklists, CHANGELOG under Unreleased, tracker manifest regenerated, codex mirror synced twice idempotently (R6 — docs-site downstream deliberately left to the conductor per dispatch). Baseline: green (focused test_spec_ready pre-edit; spec has no Quick commands). Implementation of the flowctl surface was bridged to a grok-4.6 worker per explicit orchestration instruction; diff reviewed by this worker before integration.

stage: impl-review - ran [NEEDS_WORK -> SHIP, 2 rounds; codex:gpt-5.6-sol:high; finding fixed: capture --no-plan exact-token parse]
## Evidence
- Commits: 07ece2e10c94f364b3e28fae349214a50b955634, b03fd7401e10a0a8c8b2a5c9f6eadb4c17004b7c
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_spec_no_plan test_spec_ready test_flowctl_surface test_pilot_backlog_substrate test_capture_readiness_contract test_skill_prose_diet -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: