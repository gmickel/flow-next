---
satisfies: [R8, R9, R10, R11, R12, R13]
---
# fn-141-tracker-determinism-c-prose-teardown.4 Supersede fn-57 R3; rewrite repo docs

## Description
Record the fn-57 R3 supersession at all three assertion sites so nothing ships contradicting a live criterion: `cmd_sync_check`'s "NO tracker-mutation code lives here or anywhere in flowctl (R3)" docstring, the `list-dep-relations` transport-blind docstring, and `docs/tracker-sync.md:238`'s "flowctl has no tracker transport".

Rewrite `docs/tracker-sync.md` (Transport ladder becomes flowctl-owned; document `tracker.resolved` + capability degradation). Add `## flowctl tracker` to `docs/flowctl.md` modelled on `## flowctl sync`, covering every verb, the result envelope, class enum and numeric exit codes. Correct the Jira apiVersion default to 2.

Update the doc-index rows still using "transport ladder" as user-facing vocabulary (`README.md`, `docs/README.md`, `docs/teams.md`, `CLAUDE.md`), and re-measure `agent_docs/optimizing-skills.md`'s always-loaded weight for tracker-sync.

## Acceptance
- [ ] All three fn-57 R3 assertion sites updated with a pointer to this batch
- [ ] docs/flowctl.md has a complete `## flowctl tracker` section incl. envelope + class enum + exit codes
- [ ] Jira apiVersion default corrected to 2
- [ ] No doc teaches runtime transport-ladder reasoning (all four index rows)
- [ ] optimizing-skills.md weight re-measured

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
