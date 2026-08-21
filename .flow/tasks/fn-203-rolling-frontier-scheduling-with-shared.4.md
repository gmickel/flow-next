---
satisfies: [R3, R4, R5, R6, R7]
---
# fn-203-rolling-frontier-scheduling-with-shared.4 Beta work skill (thin delta) with rolling scheduler + notes surface

## Description
Ship the winning arm as a user-invoked experimental-tier beta skill. GATED: implement only after task 3 records a passing arm.

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
- Depends on task 5 (not just task 3): if arm 2 won, the scheduler reference invokes the commit-mutex verb task 5 ships; if arm 1 won, task 5 closes with its skip note first. Either way this task starts against a settled dependency.
- Canonical work files are byte-unchanged in this task (R3) - prose-pin suites for work stay green untouched (R8).
- Pilot/land never dispatch the beta (spec Boundaries) - the guide-routing decision must not wire it into the pipeline.
## Acceptance
- [ ] Beta skill exists as thin delta; canonical flow-next-work files byte-unchanged (git diff proof)
- [ ] Admission rule + report lines behave per R4 on a dogfood run; planSync=true degrades to serial
- [ ] SHIP gates done per task; reviewer surfaces byte-unchanged (R5)
- [ ] Winning-arm integration path implemented per R6 (join reuse, or mutex+staging+ledger)
- [ ] Notes dir created/keyed/deleted per R7; creation failure degrades advisory
- [ ] sync-codex.sh run twice, idempotent, guards green; conduct checklist added and dogfood pass/fail marked
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
