---
satisfies: [R6]
---
# fn-203-rolling-frontier-scheduling-with-shared.5 flowctl commit-mutex verb + focused tests (only if arm 2 wins)

## Description
The one mechanical flowctl surface: a commit mutex (acquire/run/release around a worker's stage-and-commit). CONDITIONAL: implement only if task 3 crowns arm 2 (shared checkout); if arm 1 wins, close this task with a skip note recorded.

<!-- Updated by plan-sync: fn-203.3 recorded arm 1 (rolling + isolated workspaces) as the winning architecture, 2026-08-22; arm 2 (shared checkout + commit mutex) FAILED quality parity (33/42 vs baseline 37/42). This task's precondition resolves to the skip-note path: close unimplemented, no flowctl change, per spec R2/Decision Context. -->

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
Not applicable: the condition was 'only if arm 2 wins'. Arm 1 (isolated worktrees) won; no commit-mutex verb was built. Recorded as done-by-condition on 2026-09-04 so the spec can close honestly.
## Evidence
- Commits: c821b999, afdf5e57
- Tests: agent-evals studies/rolling-frontier-2026-08 (PREREGISTER.md frozen pre-draw; A0 129.1 min, A1 61.9 min, 52.1% saving, decisive band)
- PRs: https://github.com/gmickel/flow-next/pull/365, https://github.com/gmickel/flow-next/pull/376