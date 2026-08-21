---
satisfies: [R10]
---
# fn-203-rolling-frontier-scheduling-with-shared.7 Phase C: graduation or sunset decision + execution

## Description
After the pre-declared field window (minimum count of beta-run specs with receipts, as recorded in the task-6 CHANGELOG entry), execute the recorded decision. There is no third outcome in which both topologies remain.

**Size:** M
**Files:** graduation: plugins/flow-next/skills/flow-next-work/phases.md + references/wave-join.md (Phase 3 replaced), beta skill dir deleted, sync-codex entries removed, conduct files updated, prose-pin suites updated deliberately, docs rewritten (orchestration/architecture/flowctl/skills.md), CHANGELOG; sunset: deletions + CHANGELOG only
**Touches:** [plugins/flow-next/skills/flow-next-work/**, plugins/flow-next/skills/<beta-skill-dir>/**, scripts/sync-codex.sh, agent_docs/conduct/**, plugins/flow-next/docs/**, plugins/flow-next/codex/**, CHANGELOG.md]

### Approach
- Decision inputs: field receipts from beta runs (admission report lines, incident-shaped escalations, review outcomes) mined against the same incident classes the eval counted; the decision and its evidence recorded in this spec before execution.
- Graduation: scheduler replaces canonical work Phase 3 and the beta is deleted in the SAME change (removal is the adding-skills checklist run backwards); work prose-pin suites updated deliberately with rationale in the commit message (R8 Phase C clause); agent_docs/conduct/work.md updated same-change; this is a default-behavior change to the highest-traffic skill - full user-facing release treatment.
- Sunset: delete the beta (same removal checklist), CHANGELOG line says it was experimental and is gone, reason recorded in the spec.
## Acceptance
- [ ] Field window satisfied and decision + evidence recorded in the spec before execution
- [ ] Exactly one topology remains after the change (graduated canonical, or canonical-as-before)
- [ ] Removal/replacement checklist fully walked; full gate green; CHANGELOG entry matches the outcome
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
