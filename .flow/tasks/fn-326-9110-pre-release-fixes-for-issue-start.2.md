---
satisfies: [R6, R7, R8, R10]
---
# fn-326-9110-pre-release-fixes-for-issue-start.2 Tracker fixes: capture merge-base seed, Linear default labels, GitLab host port

## Description
R6 (moved from task 1, which stopped BLOCKED: DESIGN_CONFLICT on it): an issue start's capture push reports a backlog-vs-ready status conflict for an issue in the ready lane. Task 1 traced it to decide() in flowctl_tracker/status/policy.py, not to when `spec ready` runs: decide('backlog', None, 'backlog', 'todo', 'none') returns a conflict whatever the readiness. Its suggested fix was an early-agreement check in decide() when {flow_norm, tracker_norm} == {"todo", "backlog"} and requested_to in ("todo", "backlog"); verify that does not hide a real conflict elsewhere (backlog mode, reconcile, the readyState projection), add a policy test, and record a live Linear push (issue in Todo, spec just captured) showing no conflict.

Docs follow-ups from task 1 (same task, docs only): plugins/flow-next/docs/tracker-sync.md documents `wire question --reply-settles`, and plugins/flow-next/docs/flowctl.md documents `specs --refs --tracker-id <id>` (it fails closed on an unreadable spec JSON).

R7: capture's named-issue merge-base seed (fn-324, skills/flow-next-capture/references/tracker-integration.md and the flowctl path it calls) stores the tracker half as trackerBodyForMerge(issue body); an unchanged issue whose body ends in a newline or carries a flow:deps region must not return tracker_diverged on first push. R8: Linear wire list_open selects labels only for compact requests (--any-lane/--unlinked); the default query and rows match 9.10.0 (test against a fixed baseline query string, not the same revision's provider). R10: a self-managed GitLab host on a non-default port (tracker.perTracker.host http://localhost:8929) keeps its port in glab's --hostname; record tracker resolve and list-open live against http://localhost:8929 project flownext/flownext (glab is logged in there as root).

Touches: plugins/flow-next/skills/flow-next-capture/references/tracker-integration.md, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/scripts/flowctl_tracker/status/policy.py, plugins/flow-next/tests/test_tracker_status_policy.py, plugins/flow-next/docs/flowctl.md, plugins/flow-next/scripts/flowctl_tracker/wire/linear.py, plugins/flow-next/scripts/flowctl_tracker/wire/__init__.py, plugins/flow-next/scripts/flowctl_tracker/types.py, plugins/flow-next/scripts/flowctl_tracker/providers/gitlab.py, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json, plugins/flow-next/codex/, plugins/flow-next/tests/test_tracker_list_open_intake.py, plugins/flow-next/tests/test_tracker_syncbody.py, plugins/flow-next/docs/tracker-sync.md

## Acceptance
R6, R7, R8 and R10 of the parent spec hold, plus the two docs follow-ups, with the tests and the live GitLab recording they name.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
