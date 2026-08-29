---
satisfies: [R7]
---
# fn-211-feature-map-compounding-user-pov-drive.3 Consumers: qa + drive read the map by pointer; stale routes file as drift memos

## Description
Wire the two consumers. Greenfield: neither skill references `.flow/features/` today. Split as its own task because it touches different files than tasks 1-2 (parallel candidate with task 2) and its contract is consumption, not authoring.

**Size:** S/M
**Files:** `plugins/flow-next/skills/flow-next-qa/workflow.md`, `plugins/flow-next/skills/flow-next-qa/SKILL.md` (one description clause), `plugins/flow-next/skills/flow-next-drive/SKILL.md`
**Touches:** [plugins/flow-next/skills/flow-next-qa/**, plugins/flow-next/skills/flow-next-drive/**]

### Approach
- QA: in the discover phase (`workflow.md:83-171` region), add the existence-gated map read - when `.flow/features/` exists, select features deterministically by the contract's `**Surface:**` identifier + sub-feature IDs (the surface the run targets), then load the matching files' "How to get to it" / "Driving it" / "Gotchas" for navigation, preconditions, and traps; scenario derivation (`:165-171` mapping table) cites map-sourced routes instead of re-deriving them. Absent map: byte-identical behavior, zero added cost beyond one existence check. The spec still supplies THIS run's ACs/R-IDs; live captured evidence remains the only SHIP basis (R7 - restate nothing, the qa verdict contract is untouched).
- QA stale-route filing: when a mapped route does not match the live app, file a `knowledge`-track memory entry tagged `feature-map-drift` (title names the feature + route; body: expected vs observed, one line each) - QA never edits the map mid-run (R6/R7). Follow qa's existing memory-filing call shape.
- drive: one short existence-gated pointer in the surface-detection step (`SKILL.md:9-30` region) - when a map exists, its feature files pre-resolve the route and gotchas; detection remains the fallback. Keep it to a few lines; the map contract lives in the features skill's references (one page, one job).
- Mind fn-173 overlap: these are the same files its cua work touches - keep edits surgical so either lands first and the other rebases cleanly.
## Acceptance
- [ ] QA discover phase consumes the map behind an existence check, selecting by Surface identifier + sub-feature IDs; absent map = unchanged behavior
- [ ] Scenario derivation cites map routes when present; spec ACs/R-IDs and live-evidence SHIP basis untouched
- [ ] Stale routes file as knowledge-track memory tagged feature-map-drift; QA never edits the map
- [ ] drive carries the short pre-resolved-route pointer with detection as fallback
- [ ] No duplicated map-contract prose in either consumer (pointers only)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
