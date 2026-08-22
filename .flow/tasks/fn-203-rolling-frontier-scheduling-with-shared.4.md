---
satisfies: [R3, R4, R5, R6, R7]
---
# fn-203-rolling-frontier-scheduling-with-shared.4 Beta work skill (thin delta) with rolling scheduler + notes surface

## Description
Ship the winning arm as a user-invoked experimental-tier beta skill. GATED: implement only after task 3 records a passing arm. <!-- Updated by plan-sync: fn-203.3 recorded arm 1 (rolling + isolated workspaces) as the passing arm -->

**Size:** L->M (bounded by the thin-delta rule: one SKILL.md + one scheduler reference; everything else consumed from canonical work by pointer)
**Files:** plugins/flow-next/skills/<beta-skill-dir>/SKILL.md, plugins/flow-next/skills/<beta-skill-dir>/references/<scheduler>.md, command shim, scripts/sync-codex.sh (REQUIRED_OPENAI_YAML_SKILLS + generate_openai_yaml entries), agent_docs/conduct/<beta>.md + conduct/README.md row, flow-next-guide SKILL.md routing decision
**Touches:** [plugins/flow-next/skills/<beta-skill-dir>/**, plugins/flow-next/commands/**, scripts/sync-codex.sh, agent_docs/conduct/**, plugins/flow-next/skills/flow-next-guide/SKILL.md, plugins/flow-next/codex/**]

### Approach
- Follow agent_docs/adding-skills.md in full, including its experimental-tier section: frontmatter description ends with the experimental marker; README/skills.md rows are skipped per that tier; command shim, sync-codex entries, conduct checklist, and the guide-routing decision are NOT skipped.
- Thin delta (R3): the SKILL.md orients and defers to canonical flow-next-work phases/references by pointer for everything except Phase 3; the scheduler reference carries rolling admission (R4), conductor-owned review (R5), winning-arm integration (R6), and the notes surface (R7). No cross-skill pointer precedent exists - the beta's preamble must state its own resolution rung for locating the canonical work skill's files (same three-rung shape as the flowctl preamble).
- Notes surface: keyed by spec id + run identifier under the state-dir sibling; conductor creates at Phase 3 start, deletes on clean completion; read-by-pointer rule in prose.
- Verify (not assume) cross-run claim semantics: beta and canonical runs on the same spec contend on the same spec-scoped claims and fail closed - demonstrate once and note it in the conduct checklist.
- Conduct checklist: state assertions per emission variant (per arm branch if both shapes survive into prose), per the split-at-second-adjacent-finding lesson.
- Dogfood once on a real multi-task spec before handoff; capture the admission report lines as evidence.

### Key context
<!-- Updated by plan-sync: fn-203.3 recorded arm 1 (rolling + isolated workspaces) as the winning architecture; arm 2 (shared checkout + commit mutex) failed on quality parity. -->
- Depends on task 5: arm 1 won (fn-203.3, 2026-08-22), so task 5 closes unimplemented with a skip note first (no commit-mutex verb ships). This task's scheduler reference builds arm-1 integration only - per-task worktree integration reusing the wave-join evidence and SHA normalization - never the mutex/staging-by-declaration/edit-state-ledger machinery.
- Canonical work files are byte-unchanged in this task (R3) - prose-pin suites for work stay green untouched (R8).
- Pilot/land never dispatch the beta (spec Boundaries) - the guide-routing decision must not wire it into the pipeline.
## Acceptance
- [ ] Beta skill exists as thin delta; canonical flow-next-work files byte-unchanged (git diff proof)
- [ ] Admission rule + report lines behave per R4 on a dogfood run; planSync=true degrades to serial
- [ ] SHIP gates done per task; reviewer surfaces byte-unchanged (R5)
- [ ] Winning-arm integration path implemented per R6: arm 1 - per-task integration reuses the wave-join evidence and SHA normalization; a join conflict retries that task serially <!-- Updated by plan-sync: fn-203.3 used arm 1, not arm 2 mutex+staging+ledger -->
- [ ] Notes dir created/keyed/deleted per R7; creation failure degrades advisory
- [ ] sync-codex.sh run twice, idempotent, guards green; conduct checklist added and dogfood pass/fail marked
## Done summary
Shipped the fn-203 Phase B beta: experimental skill flow-next-work-rolling as a thin delta over canonical work (SKILL.md + references/rolling-scheduler.md; everything else consumed by pointer via a three-rung WORK_SKILL resolution). The scheduler implements arm-1 rolling admission (five fail-closed conditions vs the in-flight set, cap 3, per-event recomputation, In-flight/Admitted/Held report lines), an event-driven conductor-owned review lifecycle (review launched concurrently at worker return; SHIP routes done -> 3d.1 -> 3e plan-sync barrier -> slot free; NEEDS_WORK fix loop never blocks admission), per-task wave-join integration with SHA normalization and serial collision retry, planSync=true serial degradation, and the outside-tree notes surface (spec id + run id keyed, pointer-only, deleted after canonical Phase 5, advisory on creation failure). Command shim, sync-codex REQUIRED+openai.yaml entries (explicit-false catalog), guide routing decision (never a default route), conduct checklist with dogfood record, registry counts 27/31 per the experimental-tier carve-out, and a /bin/bash 3.2 compat fix for the fn-202 docs-link guard. Canonical flow-next-work files byte-unchanged.

stage: impl-review - ran [r1 NEEDS_WORK (4 findings), r2 NEEDS_WORK (1 new P1, 2 declined-with-evidence), r3 SHIP] (model: codex/gpt-5.6-sol)
## Evidence
- Commits: e4bec4d8e83e5705810daebe41533c402936e88c, fb41b6f8b2359d61b61702174f209c8fc1048778, 113c06ec9dc7c20cd0ddbec4156a9d97a9bea458, 1c1863fbf7497ce4528cd4d99db5d8a0b051f95e
- Tests: baseline: green - cd plugins/flow-next/tests && python3 -m unittest test_parallel_work_prose test_worker_anchor_prose test_cp1252_robustness -q (23 tests OK, pre-edit), python3 scripts/run_tests_parallel.py (full suite, 4437 tests OK at 1c1863fb; green receipt minted gate=unittest), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent, all guards green), dogfood: rolling admission events E0-E3 on real 5-task fixture fn-174 (isolated clone + FLOW_STATE_DIR); planSync=true -> Sequential fallback reported; notes dir create/key/delete + advisory degrade; cross-actor claim contention rc 1, canonical byte-unchanged proof: git diff over skills/flow-next-work + agents/worker.md = 0 lines
- PRs:
stage: plan-sync - ran (field-window ownership corrected: .6 records it; .7 provenance fixed)
