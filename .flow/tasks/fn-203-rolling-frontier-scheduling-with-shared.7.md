---
satisfies: [R10]
---
# fn-203-rolling-frontier-scheduling-with-shared.7 Phase C: graduation or sunset decision + execution

## Description
After the pre-declared field window (minimum count of beta-run specs with receipts, as recorded in the spec's Decision Context by task 6 - not task 3, which shipped the beta in .4 without recording it - and repeated in the task-6 CHANGELOG entry), execute the recorded decision. There is no third outcome in which both topologies remain. <!-- Updated by plan-sync: fn-203.4 reviewer flagged the field window was never recorded by task .3; task .6 now carries that item -->

**Size:** M
**Files:** graduation: plugins/flow-next/skills/flow-next-work/phases.md + references/wave-join.md (Phase 3 replaced), plugins/flow-next/skills/flow-next-work-rolling/** + command shim deleted, guide routing reverted, sync-codex entries removed, conduct files updated, prose-pin suites updated deliberately, docs rewritten (orchestration/architecture/flowctl/skills.md), CHANGELOG; sunset: deletions (skill dir, command shim, guide route, sync-codex entries, conduct files) + CHANGELOG only <!-- Updated by plan-sync: fn-203.4 named the beta skill dir flow-next-work-rolling -->
**Touches:** [plugins/flow-next/skills/flow-next-work/**, plugins/flow-next/skills/flow-next-work-rolling/**, plugins/flow-next/commands/**, plugins/flow-next/skills/flow-next-guide/SKILL.md, scripts/sync-codex.sh, agent_docs/conduct/**, plugins/flow-next/docs/**, plugins/flow-next/codex/**, CHANGELOG.md]

### Approach
- Decision inputs: field receipts from beta runs (admission report lines, incident-shaped escalations, review outcomes) mined against the same incident classes the eval counted; the decision and its evidence recorded in this spec before execution.
- Graduation: scheduler replaces canonical work Phase 3 and the beta is deleted in the SAME change (removal is the adding-skills checklist run backwards); work prose-pin suites updated deliberately with rationale in the commit message (R8 Phase C clause); agent_docs/conduct/work.md updated same-change; this is a default-behavior change to the highest-traffic skill - full user-facing release treatment.
- Sunset: delete the beta (same removal checklist), CHANGELOG line says it was experimental and is gone, reason recorded in the spec.
## Acceptance
- [ ] Field window satisfied and decision + evidence recorded in the spec before execution
- [ ] Exactly one topology remains after the change (graduated canonical, or canonical-as-before)
- [ ] Removal/replacement checklist fully walked; full gate green; CHANGELOG entry matches the outcome
## Done summary
Decision (Gordon, 2026-09-04): GRADUATE. Rolling works in the field and the measured saving is 52% at the decisive band. Execution is a separate spec: fold the rolling scheduler into the official work skill as a conditional route selected via progressive discovery, then retire work-rolling. See the follow-up spec created the same day.
## Evidence
- Commits: c821b999, afdf5e57
- Tests: agent-evals studies/rolling-frontier-2026-08 (PREREGISTER.md frozen pre-draw; A0 129.1 min, A1 61.9 min, 52.1% saving, decisive band)
- PRs: https://github.com/gmickel/flow-next/pull/365, https://github.com/gmickel/flow-next/pull/376