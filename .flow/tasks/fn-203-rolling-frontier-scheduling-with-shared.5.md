---
satisfies: [R6]
---
# fn-203-rolling-frontier-scheduling-with-shared.5 flowctl commit-mutex verb + focused tests (only if arm 2 wins)

## Description
The one mechanical flowctl surface: a commit mutex (acquire/run/release around a worker's stage-and-commit). CONDITIONAL: implement only if task 3 crowns arm 2 (shared checkout); if arm 1 wins, close this task with a skip note recorded.

**Size:** S
**Files:** plugins/flow-next/scripts/flowctl.py, plugins/flow-next/tests/<new focused test module>, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json (regenerated), codex mirror (regenerated)
**Touches:** [plugins/flow-next/scripts/flowctl.py, plugins/flow-next/tests/**, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json, plugins/flow-next/codex/**]

### Approach
- Reuse the existing cross_process_lock context manager (flowctl.py ~lines 42-99: fcntl/msvcrt kernel lock, bounded 30s poll, CrossProcessLockError) - never a new lock implementation; lock file under the runtime state dir's locks/ subdir.
- Follow an existing thin-verb shape for CLI plumbing; JSON output; no config key (no schema regen needed - confirm, else extend gen_flow_config_schema per repo rules).
- Focused deterministic tests: two contenders serialize; timeout raises with a clear diagnostic; lock released on process death.

### Key context
- fn-191 (review-terminal extraction) and fn-190 (startup entry) are open specs touching other regions of flowctl.py - keep this addition small and self-contained to minimize merge churn; rebase rather than restructure if they land first.
- flowctl.py edits require regenerating the distribution manifest (`python3 scripts/gen_tracker_manifest.py` refreshes plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json) + `./scripts/sync-codex.sh` twice, per the repo checklist - the old single-file SOURCE_SHA256 pin was replaced by the manifest (fn-139.5); `test_tracker_distribution` fails otherwise.
## Acceptance
- [ ] Verb exists with bounded-wait semantics reusing cross_process_lock; JSON output
- [ ] Focused tests green; tracker manifest/schema untouched or regenerated as the repo rules require
- [ ] If arm 1 won: task closed unimplemented with skip note, no flowctl change
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
