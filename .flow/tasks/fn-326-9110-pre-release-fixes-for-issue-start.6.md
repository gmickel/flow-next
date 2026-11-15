---
satisfies: [R13]
---
# fn-326-9110-pre-release-fixes-for-issue-start.6 make-pr commits and pushes the tracker sync state it writes

## Description
make-pr's tracker step (skills/flow-next-make-pr/tracker-finalize.md) writes sync state, and for an unlinked spec the tracker link it creates, into .flow/specs/<spec>.json after the PR push; that write never reaches the PR or main, so land's Done step (reads the PR head's spec) misses a link make-pr created and a later sync can duplicate the issue. Commit that JSON alone and push it to the PR head branch after the tracker call; a failed push warns.

Touches: plugins/flow-next/skills/flow-next-make-pr/tracker-finalize.md, plugins/flow-next/codex/skills/flow-next-make-pr/tracker-finalize.md, plugins/flow-next/tests/test_tracker_caller_execution.py, agent_docs/conduct/make-pr.md

## Acceptance
R13 holds: a fence test shows the changed spec JSON committed alone and on the PR branch, and no commit when it is unchanged; task 5's e2e run shows it live.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
