---
satisfies: [R1]
---
# fn-181-state-provenance-status-source-review.1 flowctl show/list: status_source provenance field + absent-runtime advisory

## Description
Spec fn-181 item 1 (#304 half 1). status_source: "flow-state"|"committed" on show/list --json (always present); one plain-output advisory line when the runtime dir is absent. The merge code already knows which store answered.

**Files:** plugins/flow-next/scripts/flowctl.py (show/list merge path) + `.flow/bin/flowctl.py` dual copy; show/list tests

## Acceptance
R1 of the spec.

## Done summary
Added status_source provenance ("flow-state"|"committed") to show/list --json via merge_task_runtime (stamped at merge, stripped on every persisted write), plus one plain-output advisory line when the runtime state dir is absent. Field always present under --json; no merge-semantics change. 12 new tests (test_status_source.py).
## Evidence
- Commits: 19577611
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_status_source -q
- PRs: