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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
