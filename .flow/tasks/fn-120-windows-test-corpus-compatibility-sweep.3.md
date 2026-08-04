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

<!-- Updated by plan-sync: fn-120.1's fresh windows-2025 characterization (930cd764, run 30902967690) shows test_backend_spec.py PASSING in 4.4s -- the 900s hang described above did NOT reproduce on the current runner image. Re-verify reproduction under this task's own bounded/verbose run before assuming a live hang to bisect; if it stays green, this task still owes the R11 runner process-tree cleanup + synthetic regression and should record that no hang recurred (do not skip the exclusion removal or cleanup work on that basis alone). -->

<!-- Updated by plan-sync: fn-120.2 already investigated the scripts/run_tests_parallel.py:153 child-spawn encoding candidate (universal_newlines=True, no encoding kwarg) and deliberately left it unchanged after codex review -- parent/child already share the locale, so transport was symmetric with no live corruption, and forcing PYTHONIOENCODING=utf-8 on children would destroy the Windows leg's ability to catch the real cp1252 print-crash class fn-120.1 hit. Evidence: windows-latest run 30913423957 recorded as proof a Windows child's own unittest stream is cp1252. fn-120.2's done summary explicitly defers "runner encoding: pin or leave locale-faithful" to this task as a decision point -- treat it as one and weigh it against this recorded rationale rather than re-deriving from scratch; do not re-flag it as an open unchecked candidate. -->

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
