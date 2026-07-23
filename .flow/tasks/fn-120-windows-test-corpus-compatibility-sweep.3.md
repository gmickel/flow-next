---
satisfies: [R6, R7, R8, R10, R11]
---
# fn-120-windows-test-corpus-compatibility-sweep.3 Fix backend hang and prove zero-exclusion Windows corpus

## Description
Find and fix the Windows backend-spec hang, harden runner process-tree cleanup, and remove the final exclusion.

**Size:** L
**Files:** plugins/flow-next/tests/test_backend_spec.py, plugins/flow-next/scripts/flowctl.py backend/subprocess helpers if proven, scripts/run_tests_parallel.py, runner regression tests, .github/workflows/test-flow-next.yml

### Approach

Use bounded per-test verbose Windows runs to bisect the hanging case. Capture child commands, stdin/pipe configuration, active processes, elapsed time, and timeout cleanup. Fix the narrow backend wait/handle cause and add regressions for both success and timeout cleanup; do not raise the 900-second ceiling.

Independently make runner cleanup unconditional: close stdin; use POSIX process groups and a Windows process-tree strategy; terminate descendants on timeout; bound post-kill collection. Add a synthetic runner regression whose grandchild holds stdout, asserting rc=124, timed-out filename, elapsed time, captured output, and descendant termination. Remove the last exclusion in the same commit as the backend/runner fix and focused Windows proof.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_backend_spec -v
python3 scripts/run_tests_parallel.py
```

## Acceptance
- [ ] The exact hanging test and child-process/handle cause are documented from a bounded Windows run.
- [ ] Backend and synthetic runner regressions prove normal completion and timeout cleanup with no orphan descendant or inherited interactive stdin on POSIX and Windows.
- [ ] `test_backend_spec.py` finishes below the existing file timeout on Windows; timeout is not increased.
- [ ] The final exclusion and Windows `EXCLUDES` block are removed in the same commit as the fix.
- [ ] Permanent timeout diagnostics report file, elapsed time, rc=124, and captured output with bounded post-kill collection.
- [ ] Focused Windows proof uses the exact commit SHA and records its workflow run URL/ID.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
