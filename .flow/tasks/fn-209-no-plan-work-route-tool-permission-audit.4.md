---
satisfies: [R8]
---
# fn-209-no-plan-work-route-tool-permission-audit.4 flowctl next: surface the zero-task spec state

## Description
Reconcile `cmd_next`'s silent zero-task fall-through (empty task maps skip every branch; spec silently skipped) with the route: surface the state instead of skipping it silently.

**Size:** S-M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/tests/test_next_zero_task.py` (new)
**Touches:** [plugins/flow-next/scripts/flowctl.py, plugins/flow-next/docs/flowctl.md, plugins/flow-next/tests/test_next_zero_task.py]

### Approach
- `flowctl.py` `cmd_next` (~:34134-34333): a non-closed spec with zero tasks currently builds empty maps and falls to the next spec / `status: none`. Decide the surfaced shape against the doc'd contract at `docs/flowctl.md:870-883` (statuses `plan|work|completion_review|none`): emitting `status: plan` with a `needs_tasks`-style reason for the first zero-task spec mirrors pilot's classification and is the recommended resolution; a documented deliberate skip is the acceptable fallback if the surfaced form breaks existing consumers (check pilot + ralph consumers of `next` output first).
- Regression test: NEW module `plugins/flow-next/tests/test_next_zero_task.py` (no test_next*.py exists today - `discover -p` currently collects 0 tests, which is exactly the false-green the memory bank warns about): zero-task open spec -> asserted surfaced state; plus the existing modules covering cmd_next stay green (locate them via `grep -l "next" tests/*.py` and run them).
- flowctl.md `### next` doc row update belongs to task 5's doc pass? NO - keep the doc edit HERE (same change, same reviewer): update `docs/flowctl.md:870-883` in this task; task 5 does not touch flowctl.md.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:34134-34333` - cmd_next body incl. empty-map path
- `plugins/flow-next/docs/flowctl.md:870-883` - documented next contract
- callers: grep pilot/ralph skills for `flowctl next` consumption before changing output shape

**Optional:**
- existing tests: `grep -l cmd_next plugins/flow-next/tests/*.py`

### Acceptance
- [ ] zero-task open spec is surfaced (recommended: status plan + reason) or the skip is documented as deliberate in code comment + flowctl.md - one of the two, explicitly
- [ ] regression test covers the zero-task path; existing next tests green
- [ ] `docs/flowctl.md` next section matches the shipped behavior
- [ ] `uvx ruff@0.16.0 check .` green
## Acceptance
- [ ] TBD

## Done summary
flowctl next now surfaces a non-closed zero-task spec as `status: plan` / `reason: needs_tasks` (the recommended shape, mirroring pilot's classification) instead of silently skipping it; docs/flowctl.md's next contract gained the reason and a behavior note, and the new deterministic module tests/test_next_zero_task.py pins the path (6 tests, zero-task cases red-first-proven against pre-edit code; done-spec skip, ready-task, and completion-review paths asserted unchanged). Consumer audit before the shape choice: ralph.sh handles `status=plan` generically (zero-task specs now route to planning rather than NO_WORK), pilot never calls `next`, work does not read it — no consumer breaks.

baseline: green (test_task_inventory + uvx ruff@0.16.0 check ., pre-edit)
gates: focused per spec Quick commands — test_next_zero_task + test_task_inventory green (suite_rc=0), ruff green; `gate classify` says FULL tier (flowctl.py touched) — full suite deferred to the conductor/finalization gate per spec Quick-commands convention, no receipt written
implementer: grok-4.6 bridge (foreground, single pass; host verified diff, fixed one assertion for json_output's `success: true`, ran tests, committed)
follow-up for task .6: flowctl.py touched — gen_tracker_manifest.py + sync-codex twice at finalization

stage: impl-review - skipped(policy: PARALLEL_WAVE + host-deferred - conductor owns the gate)
## Evidence
- Commits: 2b702c78d08c573b8b12f041d4bb172aaa51e0db, 91fda415
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_next_zero_task -q, cd plugins/flow-next/tests && python3 -m unittest test_next_zero_task test_task_inventory -q, uvx ruff@0.16.0 check .
- PRs:stage: plan-sync - skipped(config: planSync.enabled != true)
