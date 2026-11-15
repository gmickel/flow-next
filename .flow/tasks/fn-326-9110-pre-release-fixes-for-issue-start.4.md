---
satisfies: [R11]
---
# fn-326-9110-pre-release-fixes-for-issue-start.4 --auto post-merge checkout state: fix or prove harmless

## Description
After an --auto run merges its PR (land with --delete-branch), the checkout stays on the merged, remote-deleted spec branch with one sync-state file changed (seen on every gmickel/flow-next-e2e-scratch run). Establish from auto.md, the snapshot fence and land whether the next --auto run misroutes from that state (wrong base, dirty-tree stop, stale spec). If it does, fix the smallest place (likely auto.md's post-merge step: return to the default branch's remote head, keeping the sync-state write committed or discarded deliberately). If not, record why with evidence. Runs after task 1 because both edit auto.md.

Touches: plugins/flow-next/skills/flow-next-flow/auto.md, plugins/flow-next/codex/skills/flow-next-flow/auto.md, plugins/flow-next/tests/test_flow_auto.py, agent_docs/conduct/flow.md

## Acceptance
R11 holds: the finding states fixed or harmless, with the evidence (a test or a recorded next run).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
