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
- **The ralph-guard question is already answered in the spec: revert, do not widen.** The guard's delegation amendment (the canonical-invocation recognizer, the allowed sandbox-flag list, the accepted scratch-path shape) exists to bound one machine-generated command shape and reverts with it. Restore the guard to its pre-amendment behavior; add nothing for prose-routed bridges. Ralph is deprecated and predates the packaged path, so it simply returns to what it did before.
- Record the revert in the task summary and write one memory decision entry noting the accepted trade: for prose-routed bridges the safety rule is prose-only, which is weaker than a hook and deliberate.

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
