---
satisfies: [R17]
---
# fn-139-tracker-sync-determinism-flowctl-owns.9 Supersede fn-57 R3 in code and docs; full documentation pass

## Description
Record the fn-57 R3 supersession where it is asserted in code and prose, so nothing ships contradicting a live acceptance criterion: `flowctl.py` `cmd_sync_check`'s "NO tracker-mutation code lives here or anywhere in flowctl (R3)" docstring, the `list-dep-relations` transport-blind docstring, and `docs/tracker-sync.md`'s "flowctl has no tracker transport" line.

Full docs pass: rewrite `docs/tracker-sync.md` (the Transport ladder section becomes flowctl-owned), add a `## flowctl tracker` section to `docs/flowctl.md` modelled on the existing `## flowctl sync`, correct the Jira apiVersion default, update the doc-index rows that use "transport ladder" as user-facing vocabulary (README.md, docs/README.md, teams.md, CLAUDE.md), and stage a CHANGELOG entry under `## Unreleased`.

## Acceptance
- [ ] All three in-code/in-doc assertions of fn-57 R3 updated with the supersession noted
- [ ] docs/flowctl.md has a complete `## flowctl tracker` section incl. result envelope + class enum
- [ ] Jira apiVersion default corrected to 2 in docs
- [ ] No doc still teaches runtime transport-ladder reasoning
- [ ] CHANGELOG staged under Unreleased; no version bump

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
