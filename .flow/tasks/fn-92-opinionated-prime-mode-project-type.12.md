---
satisfies: [R16, R17, R18, R3]
---

## Description
workflow.md Phase 3 synthesis: AO/DR/TO/HP inline groups + scoring integration + verdict assembly.

**Size:** M | **Files:** `plugins/flow-next/skills/flow-next-prime/workflow.md` (Phase 3)

## Approach
- AO/DR/TO/HP host-inline check blocks (resolution 10) consuming Phase 2 probe output (boot/CLI evidence) and harness.md rows; DR-core four-ID evaluation for QA-readiness (amended resolution 1).
- Scoring integration per the pillars.md criterion-to-score map: five-state rules kept; whitelist referenced from the pillars.md table only (resolution 11); new-group aggregates presented as group pass-count lines, excluded from the level formula.
- Latency lines per resolution 3 with the corrected gh fields (startedAt/updatedAt local derivation on completed default-branch runs - durationMs does not exist); gh-CLI reported as an informational host-prerequisite line excluded from repo scores.
- Verdict assembly: classification + per-surface tier + gate status + top-5 from the playbooks.md tiered catalog.

## Key context
- No new scouts; groups are host-inline. Every verdict quotes evidence; HP key-name-only quoting.

## Acceptance
- [ ] AO/DR/TO/HP blocks present and consuming Phase 2 evidence; DR-core all-four QA rule wired (R16, R17)
- [ ] Scoring uses the pillars.md map + whitelist table; group aggregates never fold into the level (resolution 1)
- [ ] Latency lines use derived durations; gh-CLI is informational host line (R18 as amended)
- [ ] Verdict assembly produces the headline inputs (R3)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
