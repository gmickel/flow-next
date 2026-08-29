---
satisfies: [R5, R6]
---
# fn-211-feature-map-compounding-user-pov-drive.2 Maintain mode: audit-shaped pass with clean/changed/blocked

## Description
Add the maintain mode (maintain.md) to the skill task 1 scaffolded. Split from task 1 so the seed/contract foundation is stable before the upkeep loop is written against it (R5 depends on the R3/R4 contracts).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-features/maintain.md`, `plugins/flow-next/skills/flow-next-features/SKILL.md` (mode wiring only)
**Touches:** [plugins/flow-next/skills/flow-next-features/**]

### Approach
- maintain.md opens with the standard three-rung FLOWCTL preamble (it invokes `flowctl memory search`/`memory add` itself; every top-level file that calls flowctl carries the preamble - house convention).
- The pass, in order, each phase with a Done-when gate (QA workflow's house pattern): (1) index hygiene - fix missing/extra/duplicate/dead entries, consume `feature-map-drift` memory entries via `flowctl memory search` (spec Decision Context); (2) source wave - one read-only reader per feature, dispatched concurrently via the existing read-only scout dispatch shape (Task with a read-only subagent; portable-host fallback clause; readers never drive, never edit; return shape: feature summary / source entry points / likely drift or none / one live recipe); reader error or timeout marks that feature blocked-for-this-pass, pass continues; (3) reconcile - merge recipes into as few app states as practical, spot-check cited drift only, sweep recent churn for unmapped user-facing surfaces (concrete source path required); (4) live pass - required even when source looks clean; Doctor discipline from references/doctor-and-proof.md; every feature exercised once; `verified-unreachable` only with the concrete prerequisite + attempted route (an unstated prerequisite is itself drift); harness fixes re-driven before shipping; final teardown after the last drive, evidence survives; (5) triage - doc drift -> fix map; harness gap -> fix + re-drive; product bug -> report, NEVER in the PR (R6 edit scope: map dir + owned harness scripts only); (6) ship or stop.
- Outcomes exactly `clean` (no branch, no PR) / `changed` (one PR of proven corrections, every changed file re-read first) / `blocked` (names what blocked; terminal for the invocation, next run re-enters fresh - no resume state).
- PR mechanics for `changed` (spec Decision Context): commit to a fresh branch, open a chore PR directly with a hand-written body matching the make-pr STRUCTURE (summary / what changed / per-feature outcomes / evidence pointers) - never invoke /flow-next:make-pr, never merge.
- Run notes + live evidence under the gitignored per-run tmp convention QA uses; the `changed` PR carries `.flow/features/**` plus owned harness corrections (a proven harness fix ships, or a clean checkout stays undrivable) - run notes, scratch state, and evidence stay out, referenced by path without pretending they are reviewable post-merge.
- Assemble any structured output with jq, never free-form prose interpolated into heredoc JSON (memory `heredoc-built-json-breaks-on-free-form-2026-06-05`).

### Investigation targets
**Required** (read before writing):
- `plugins/flow-next/skills/flow-next-audit/workflow.md` - the audit-shaped outcome loop this mirrors
- `plugins/flow-next/skills/flow-next-qa/workflow.md:402-520` - typed receipt/outcome emission pattern
- Task 1's seed.md + references (the contracts maintain enforces)
## Acceptance
- [ ] Maintain phases 1-6 present with Done-when gates; source readers are concurrent, read-only, failure-isolated
- [ ] Outcomes exactly clean/changed/blocked with the stated PR mechanics (hand-written chore body, no make-pr, no merge); the changed PR carries map files plus owned harness corrections, never notes/scratch/evidence
- [ ] `verified-unreachable` requires prerequisite + attempted route; product bugs reported and excluded from the PR (R6)
- [ ] Drift-tag memory consumption in index hygiene; run notes/evidence in gitignored per-run tmp
- [ ] `blocked` is terminal with fresh re-entry; no resume/checkpoint machinery introduced
- [ ] maintain.md carries the three-rung FLOWCTL preamble
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
