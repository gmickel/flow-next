---
satisfies: [R2, R9, R12]
---
# fn-130-reached-path-skill-prompt-optimization.8 Gate Work delegation-only machinery

## Description
Move Codex delegation-only Phase 1.5 and circuit-breaker instructions behind the existing delegation reference while preserving the complete Work lifecycle, fn-118 sanctioned parallelism, host-owned git, tracker/review gates, and plan-sync-after-wave behavior.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/{SKILL.md,phases.md,references/codex-delegation.md,references/tracker-sync.md}`, Work/parallel/delegation/prose tests and route fixtures, `optimization/reached-path/work-*`, corresponding Codex mirror.

### Approach
- Keep ordinary task anchor, baseline checks, serial/parallel wave judgment, worker dispatch/join, review, commit, status, and plan-sync common.
- Route delegation only after config/argument/consent selection; inactive/declined paths must not load delegation implementation or circuit-breaker prose.
- Preserve fn-103 path-handoff rails and do not regrow the deleted composed Codex brief.
- Preserve fn-118 conflict screening, optional isolation, worker failure handling, host-deferred handover, host ownership of git/commit, and plan-sync after the integrated wave.
- Keep tracker sentinel fail-open behavior and every terminal cleanup; do not create a deterministic semantic plan-sync skip gate.

### Frozen fixtures
- serial task; parallel eligible disjoint tasks; shared-file/generated-resource conflict; worker failure; host-deferred integration.
- delegation disabled, enabled+consent, enabled+decline, CLI unavailable, implementation failure, circuit breaker.
- tracker inactive/active/probe error; review pass/fail; plan-sync no-op/update; autonomous markers.

### Investigation targets
**Required**
- `plugins/flow-next/skills/flow-next-work/phases.md:32-61` — delegation phase.
- `plugins/flow-next/skills/flow-next-work/phases.md:128-158` — circuit breaker and host gates.
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` — existing selected-path owner.
- `plugins/flow-next/tests/test_parallel_work_prose.py:30-262` — fn-118 contracts.
- `plugins/flow-next/tests/test_codex_delegation_gates.py` and `test_work_delegate_config.py` — delegation states.

**Optional**
- `.flow/memory/knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19.md`.
- `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`.

## Acceptance
- [ ] Task input prompt hashes match version-adjusted `V1/B1`; every structural candidate compares against `B1`, never original `B0`.
- [ ] Baseline and candidate traces cover serial, parallel, conflict, worker failure, host-deferred, delegation, tracker, review, plan-sync, and autonomous states.
- [ ] Delegation-off/declined paths do not load delegation-only machinery; active paths load the complete consent/path-handoff/circuit-breaker contract.
- [ ] fn-118 isolation/conflict/join/host-git/plan-sync semantics and fn-103 path handoff remain unchanged; no composed brief or deterministic plan-sync skip gate regrows.
- [ ] Every tracker/review/error terminal, cleanup, receipt/status slot, and commit ownership behavior matches baseline.
- [ ] Existing parallel/delegation/tracker/prose tests plus canonical/mirror route assertions pass.
- [ ] Measured default-path reduction is recorded; any unsafe extraction is reverted and logged without further prose trimming.
## Done summary
Optimized Work's reached prompt path while preserving the fn-118 wave lifecycle, fn-103 path handoff and safety rails, tracker fail-open routing, review ordering, and plan-sync timing. Conductor review caught and repaired a circular summary-first consent router: delegation-off loads no reference; requested delegation loads an exact selection contract; only a passing selection loads active-only mechanics. The corrected B1-hash-anchored ratchet covers 20 behavior routes; default path shrinks 3,730 chars (6.86%) and delegation-active path shrinks 427 chars (0.42%).

Verification: B1 input check passed before mutation; focused Work suite passed; canonical and Codex mirror routing regenerated twice and reviewed; combined full suite ran 2,286 tests with 3 skips and zero failures/errors. Plugin smoke passed from its required external working directory.
## Evidence
- Commits: 0a4400f7, ed9b6206, 63e9942e, 3e4e92ee, f3d1ff79, f7c85984, e901aa00, 1ab5bb3b, 0f08c608, c00dc797, c0142c0d, 97e9793a
- Tests: ./scripts/sync-codex.sh twice: 28 skills, 22 agents, idempotent, python3 scripts/run_tests_parallel.py: 2,286 run, 3 skipped, 0 failures/errors, bash plugins/flow-next/scripts/smoke_test.sh from /tmp: 136 passed, 0 failed, flow-next.dev build: Astro check 0 errors/warnings/hints; 74 pages built, git diff --check and changed-reference existence audit: passed, Prime authenticated Claude baseline and candidate: 7/7 each; 6/6 synthetic plus negative control
- PRs:
