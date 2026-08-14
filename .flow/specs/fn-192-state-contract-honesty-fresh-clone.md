# State-contract honesty: validate on fresh clones, done-summary durability (#346, #347)

## Goal & Context

Two @sn-furali issues are two halves of one contract break: `flowctl done` is the only command that writes across the tracked/runtime durability boundary, and no surface on either side is told which half it got. Verified against main (5b9f9cec):

- **#347 (read side).** Spec status is tracked; task status is runtime-only (`save_task_runtime`, git common-dir - "Never touch definition file", flowctl.py ~:1100). `validate` compares the tracked spec status against task status and emits an ERROR "Epic marked done but task X is <status>" (~:35305-35310, unchanged since the first plugin commit). On a fresh clone runtime state is absent, task status falls back to the committed sidecar (forever `todo`), so `validate --all` fails unconditionally - reproduced: exit 1, 582 findings on this repo's own fresh clone. This directly violates the repo's fn-181 doctrine ("a task looking not-started in committed files is never grounds for a finding" - CHANGELOG 3.23.0), which shipped for reviewers but never reached `validate`. The work skill's own Phase 5 Ship runs `validate --spec` as its verify step, so the conductor's check is guaranteed-red for any spec closed on another machine.
- **#346 (write side).** `cmd_done` writes the Done summary + Evidence into the TRACKED `.flow/tasks/<id>.md` (~:34817-34825 atomic_write) immediately before writing runtime status - but the documented loop commits BEFORE `done` (worker.md Phase 3 commit -> Phase 5 done; CLAUDE.md quickstart same), so the receipt misses the loop's commit. Non-final tasks get rescued by the next task's `git add -A`; the FINAL task's receipt is lost for direct-CLI and worktree-per-task callers (the /flow-next:work conductor's Phase 5 catch-all sweeps it). `done` exits 0 with no signal that it dirtied a tracked file. Worse, three doc surfaces disagree: worker.md and CLAUDE.md say commit-then-done; `templates/usage.md` ~:134-141 never mentions commit at all and tells a sandbox-blocked caller to `done` without committing.

The storage split itself is deliberate and stays (fn-181 boundary: "No change to where state lives"). The fixes make each side honest about the split.

Decision context, options rejected:
- `--stage`/`--amend` inside `cmd_done`: flowctl composing git index/commit decisions is the agentic-vs-deterministic doctrine break, `--amend` would re-orphan the evidence SHA the summary just recorded (fn-180 reachability), and index writes from concurrent wave workers sharing a common dir are a race.
- A `validate.strictStatus` config key: the durability class is knowable at runtime (`status_source` is already stamped on every task dict by `merge_task_runtime`); a key would ask the user to declare what the code already knows.

## Acceptance Criteria

- R1: in `validate`'s epic-status rule, a task whose `status_source` is the committed snapshot (runtime state absent) downgrades the "Epic marked done but task X is <status>" finding from error to WARNING, with a suffix noting the committed snapshot may be stale. Runtime-sourced mismatches stay errors. `validate` exit code stays gated on errors only (existing warnings channel). Fresh clone of a healthy repo: exit 0, findings visible as warnings.
- R2: legacy guard on R1 - when the task DEFINITION file itself carries legacy runtime fields (pre-state-dir repos, merge_task_runtime's legacy branch ~:1071-1075), committed status IS authoritative and the finding stays an ERROR. The downgrade applies only when no runtime state exists anywhere.
- R3: `cmd_done`'s `--json` payload gains `"modified_paths": [<task spec md path>]` (additive key), and when the written path is tracked-and-now-dirty (`git diff --quiet -- <path>`), `done` prints one stderr advisory naming the path and that it belongs in a commit (precedent: print_status_source_advisory shape). Exit code unchanged; Ralph/pilot/land read exit + JSON status only, so no loop behavior changes. Same treatment for `cmd_block`'s identical write-tracked-then-runtime shape (~:34875-34890).
- R4: one ordering becomes canonical across all three doc surfaces: commit-then-done, plus an explicit "stage/commit the receipt" step after done (or fold into the next commit). Surfaces: `agents/worker.md` Phase 5, `templates/usage.md` workflow steps (which currently omit commit entirely), repo-root CLAUDE.md quickstart comment. The usage.md sandbox escape-hatch line is reworded to note the receipt needs a later commit.
- R5: regression tests: (i) fresh-clone-shaped fixture (spec done, task sidecar todo, no runtime) -> warning not error, exit 0; (ii) runtime-sourced mismatch -> still error; (iii) legacy-fields-in-definition mismatch -> still error; (iv) done --json contains modified_paths; (v) dirty-tracked advisory emitted on stderr (and absent when the file was already committed). Focused suites (test_validate_all_diagnostics + the done/lifecycle suites) green.
- R6: docs: `docs/flowctl.md` validate section notes the warning class; CHANGELOG Unreleased credits @sn-furali; memory entry for the tracked-vs-runtime contract (knowledge/decisions).

## Boundaries

- Do NOT move any state between durability classes (fn-181 boundary).
- Do NOT add config keys.
- Do NOT stage, commit, or amend from inside flowctl.
- Propagation gate on flowctl.py changes (cp to .flow/bin, tracker manifest, sync-codex x2) at close-out, orchestrator-owned.
- No version bump in implementation commits; CHANGELOG under Unreleased (merge the currently duplicated Unreleased headers while there).

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_validate_all_diagnostics -q
```
