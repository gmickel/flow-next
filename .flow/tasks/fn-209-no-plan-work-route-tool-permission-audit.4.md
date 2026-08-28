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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
