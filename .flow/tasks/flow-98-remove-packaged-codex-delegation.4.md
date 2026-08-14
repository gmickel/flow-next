---
satisfies: [R6, R8]
---
# flow-98-remove-packaged-codex-delegation.4 Retire or repoint the delegation tests, and settle the ralph-guard question

## Description
Delete the tests that exist only for the packaged path, repoint the ones that assert something still true, and record the explicit decision on what the Ralph guard keeps once bridges are prose-routed.

**Size:** M
**Files:** `plugins/flow-next/tests/test_codex_delegation_classify.py`, `test_codex_delegation_gates.py`, `test_work_delegate_config.py`, `test_ralph_guard_codex_delegation.py` (delete or repoint), plus delegation assertions inside `test_model_resolution.py`, `test_hot_path_sweep.py`, `test_work_reached_path_routes.py`, `test_model_pin_ceremony_prose.py`; `plugins/flow-next/scripts/hooks/ralph-guard.py` (only if the decision says so)
**Touches:** [plugins/flow-next/tests/**, plugins/flow-next/scripts/hooks/ralph-guard.py]

### Approach
- Classify each of the four dedicated files first: purely-delegation (delete) versus asserting a surviving invariant under a delegation-shaped name (repoint, keep the substance).
- Then sweep the shared files for delegation assertions. A test that gets EASIER after this change is a regression, not a cleanup - if an assertion has to weaken, say so explicitly in the summary and justify it.
- **The ralph-guard decision is the point of this task, not a footnote.** The guard mechanically forbade a bridged child from touching git. With bridges prose-routed, either the enforcement survives for any bridged child (keep the hook, widen its trigger away from delegation-specific markers) or it is dropped and the safety rule lives only in prose (weaker, and it must be stated as such). Record which, with the reasoning, in the task summary and in a memory decision entry.
- Autonomous runs are the case that decides it: unattended loops are exactly where a prose-only rule is least reliable.

### Investigation targets
**Required** (read before coding):
- the four dedicated delegation test files - classify each
- `plugins/flow-next/scripts/hooks/ralph-guard.py` - what the guard actually enforces and how it detects a delegated child

### Key context
- Deleting a test because the feature is gone is correct; weakening a test so a diff passes is the thing this project treats as a defect.

### Acceptance
- [ ] Each of the four dedicated files deleted or repointed with the classification recorded
- [ ] Shared files carry no delegation assertions; no surviving assertion weakened without an explicit justification
- [ ] The ralph-guard decision is recorded with its reasoning (keep-and-widen, or drop-and-state-the-weakening), and a memory decision entry written
- [ ] Full suite green

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
