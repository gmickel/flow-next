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
Shipped as /flow-next:work-rolling (experimental) in PR #365: event-driven per-task admission, isolated workspaces, conductor-owned review lifecycle, plan-sync barrier, shared notes surface outside the tree. Blocking-host degradation later bound to measured dispatch behaviour (Cursor + Grok Build non-blocking) in #376. Closed retroactively 2026-09-04.
## Evidence
- Commits: c821b999, afdf5e57
- Tests: agent-evals studies/rolling-frontier-2026-08 (PREREGISTER.md frozen pre-draw; A0 129.1 min, A1 61.9 min, 52.1% saving, decisive band)
- PRs: https://github.com/gmickel/flow-next/pull/365, https://github.com/gmickel/flow-next/pull/376