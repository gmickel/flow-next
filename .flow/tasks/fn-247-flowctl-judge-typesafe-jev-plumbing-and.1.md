---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14]
---
# fn-247-flowctl-judge-typesafe-jev-plumbing-and.1 Implement flowctl judge: TypeSafe Jev plumbing and the six judged sites

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Shipped `flowctl judge` (six presets in the flowctl registry, stdlib HTTP, retry and budget rules, decision rules and floors, availability-as-fact output), `memory search --rerank`, the `judge.enabled` config key and schema entry, and the six call sites: land clean-review before the regex (report and ledger lines), flow route state assembly with the code-side lifecycle inventory, `Route:` line and `--explain` shape, the qa-gate under `pipeline.qa=auto`, the fork-gate in prototype-before-ask, the plan memory rerank replacing the scout spawn when available, and the tier decision before worker and scout spawn (spawn-model parameter plus `IMPLEMENTER:`, `TIER_LINE`, `actual_model` in the worker return). Docs: `docs/judge.md`, flowctl/platforms/README/config schema, setup key notice, call-site references, Codex mirror regenerated. Tests: `test_judge.py`, `test_judge_route.py`, `test_judge_consumers.py` cover R1-R4, every preset decision rule, the fork `none_of_the_above` case, the four PR-probe observations, the absent-`no_plan` direct route, the kind-criteria drift test against the route matrix, and per-consumer enabled and unavailable fence cases including the spawn model actually selected.

The bridged child's checkpoint (9206403f) stays; the worker range review trimmed added scope in 1964ff17: dropped the conductor-side memory retrieval and `MEMORY_FINDINGS` worker field (work never spawned a memory scout; workers keep their own `--rerank` search), moved `judge-memory.md` under the plan skill, removed a speculative key-echo check, and narrowed the `--explain` dependency scan to install/import forms after the live smoke showed it naming every backticked token.

baseline: green (python3 scripts/run_tests_parallel.py 4996 tests; ruff clean). Verify: full suite 5030 tests suite_rc=0 (receipt 1964ff17-unittest), ruff clean, sync-codex idempotent, tracker manifest regenerated, live Jev smoke on clean-review (627 ms) and route --explain.

Follow-ups noted, not built: the spec assumes work spawns a memory scout today (it does not; only plan does), so R10's "work" half is satisfied by the worker's own `--rerank` search; the `Next:`/`Skip/narrow:` presentation cells are held equal to the route matrix by `test_presentation_skip_cells_match_matrix`, a drift test beyond the kind-criteria one R13 names.

stage: impl-review - skipped(config: REVIEW_MODE=none)
stage: implement - ran (model: gpt-6-astra at medium via codex exec; delegated: 3)
## Evidence
- Commits: 9206403ffd173de649b47c34bd4aae42f0bccced, 1964ff1720865c7c4c63d78a69ec67c4148a8be6
- Tests: python3 scripts/run_tests_parallel.py (baseline: green, 4996 tests; verify: suite_rc=0, 5030 tests, 0 failures, receipt 1964ff17-unittest), uvx ruff@0.16.0 check . (baseline and verify: clean), ./scripts/sync-codex.sh x2 (idempotent, no drift), python3 scripts/gen_tracker_manifest.py, cd plugins/flow-next && python3 -m unittest tests.test_judge tests.test_judge_route tests.test_judge_consumers (34 tests OK), live smoke: flowctl judge --preset clean-review (available, jev-1.13.0, clean at >=0.7, 627 ms) and --preset route --spec fn-247 --explain (lifecycle route work_planned, clean Signal line)
- PRs: