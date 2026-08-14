---
satisfies: [R2]
---
# flow-98-remove-packaged-codex-delegation.2 Strip the delegation machinery out of the work skill and its worker

## Description
Remove the packaged delegation path from the work skill: the Phase 0 request check, the Phase 1.5 selection gate, the arg tokens, the per-worker flag appending, the circuit-breaker phase, the classify judge, and both delegation reference files. The default in-session path becomes the only path.

**Size:** M/L
**Files:** `plugins/flow-next/skills/flow-next-work/SKILL.md` (delegation activation section, arg parsing), `phases.md` (Phase 0, Phase 1.5, the 3c flag block, 3d.2), `references/codex-delegation.md` and `references/codex-delegation-selection.md` (deleted), `plugins/flow-next/agents/worker.md` (delegation phases + `DELEGATION_*` emission), `scripts/sync-codex.sh` (any delegation-specific transform or registration)
**Touches:** [plugins/flow-next/skills/flow-next-work/**, plugins/flow-next/agents/worker.md, scripts/sync-codex.sh]

### Approach
- Delete, do not deprecate. A shim that accepts `delegate:codex` and warns keeps the vocabulary alive; the migration message in .3 is the only survivor.
- Phases 0 and 1.5 exist ONLY for delegation - remove them wholly rather than emptying them, and renumber nothing else (the remaining phase numbers stay as they are; a phases file with a hole is cheaper than a renumber that breaks every prose pin pointing at a later phase).
- The worker's `DELEGATION_*` signal lines and the conductor's circuit breaker are one contract: remove both in this task or neither.
- `PARALLEL_WAVE` handling and the wave path are unrelated and must survive untouched - re-read the wave-join reference before editing 3c so the parallel branch is not damaged by proximity.
- **Grep the test corpus and `sync-codex.sh` for every literal you move or delete** before deleting it. Test-pinned means keep verbatim or retarget the test in the SAME commit; a sed/awk anchor on a deleted literal must be updated in the same change. This file also has a generator heredoc that rewrites one section of the mirror - check whether the section you touch is one of them.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-work/phases.md` Phases 0, 1.5, 3c flag block, 3d.2 - the exact removal boundary
- `plugins/flow-next/agents/worker.md` delegation phases - the other half of the signal contract
- `plugins/flow-next/skills/flow-next-work/references/wave-join.md` - what must NOT break
- `scripts/sync-codex.sh` - transforms and any hardcoded section rewrites near the edited regions

### Key context
- The classify judge is one of the sanctioned subprocess-LLM carve-outs; removing the delegation one does not touch the triage-skip judge or review-backend dispatch.

### Acceptance
- [ ] Phase 0, Phase 1.5, the arg tokens, the per-worker flags, the circuit-breaker phase, the classify judge and both reference files are gone from canonical prose
- [ ] Worker carries no delegation phases and emits no `DELEGATION_*` lines
- [ ] Wave dispatch, join, and the parallel handover contract behave exactly as before (their tests untouched and green)
- [ ] Every deleted literal checked against the test corpus and the mirror generator; retargets landed in this commit
- [ ] Mirror regenerated twice (idempotent); focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_work_reached_path_routes test_parallel_work_prose test_foreground_rule_fences -q`

## Acceptance
- [ ] TBD

## Done summary
Stripped the packaged codex-delegation machinery from the work skill and worker agent: phases.md Phase 0 + Phase 1.5 removed wholly (no renumber — hole kept), 3c DELEGATE flag block and 3d.2 circuit breaker removed (3d.1 sentinel retargeted to Phase 3e), SKILL.md activation/resolution section and arg tokens removed, both delegation reference files deleted, worker.md delegation phases + DELEGATION_* signal contract removed. WORK_CFG single root config snapshot moved into the Phase 1 spec-id mint gate (still exactly one config get; spec-id-mint.md pointer updated). Test retargets in same commit: work_reached_path_routes (anti-regrowth guard), foreground_rule_fences (no-carve-out assertion), worker_anchor_prose, skill_prose_diet. sync-codex.sh: comment reword only.

Deferred by design: mirror regen (sync-codex.sh execution, plugins/flow-next/codex/**) → task .5 per spec wave-shape rule; delegation test-file retirement → task .4.

Implemented in isolated worktree (wt/flow-98.2, e36c2859), integrated onto spec branch as afbb2ed1.

stage: impl-review - ran (host backend, fresh fable-5 reviewer, SHIP round 1; receipt /tmp/impl-review-receipt-flow-98-remove-packaged-codex-delegation.2.json; P3 worker.md:219 stale trailer sentence carried to .5)
## Evidence
- Commits: afbb2ed1202fc465e5b941ceec28fb840f7a26c2
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_work_reached_path_routes test_parallel_work_prose test_foreground_rule_fences -q (worker worktree, green), integrated verify @afbb2ed1: cd plugins/flow-next/tests && python3 -m unittest test_flow_config_schema_drift test_model_resolution test_removed_delegate_config_advisory test_work_reached_path_routes test_parallel_work_prose test_foreground_rule_fences -q (121 tests OK), uvx ruff@0.16.0 check . (All checks passed, integrated tree), python3 scripts/run_tests_parallel.py (worker worktree) -> 5 failing files ALL owned downstream: 3 delegation test files (.4), 2 mirror-parity halves (.5), impl-review: host backend SHIP (reviewer claude-fable-5, fresh read-only subagent; receipt /tmp/impl-review-receipt-flow-98-remove-packaged-codex-delegation.2.json)
- PRs: