---
satisfies: [R1, R2, R3, R7, R10, R11, R13]
---
# fn-120-windows-test-corpus-compatibility-sweep.1 Fix deterministic Windows encoding, shim, and path portability

## Description
Characterize all six exclusions on current Windows HEAD, establish permanent exact-ref diagnostic inputs, then clear the three deterministic portability failures with real CI evidence.

**Size:** L
**Files:** .github/workflows/test-flow-next.yml, plugins/flow-next/tests/test_flow_gitignore.py, plugins/flow-next/tests/test_gate_receipt.py, plugins/flow-next/tests/test_reveval_parse_guard.py, plugins/flow-next/scripts/flowctl.py only if production audit finds a real bug

### Approach

First run every excluded file separately on current `windows-latest`, before changes, and record exact current failure data. Add permanent validated `workflow_dispatch` inputs for exact-ref `suite_mode` (parallel/serial/shuffle), optional one-file pattern, verbosity, and bounded timeout; ordinary PR/push behavior remains unchanged.

Then make controlled gitignore reads explicitly UTF-8 and verify production writes/reads. Split the gate-receipt fixture along the real platform boundary: a reasoned POSIX-only skip for literal-backslash filename creation, plus an injectable status-call seam or actual Windows executable wrapper for TTL behavior; assert the double actually ran. Replace reveval string path derivation with resolved `pathlib` paths and retain the end-to-end subprocess test.

Run each fixed file alone on `windows-latest` before the combined full runner. Remove each exclusion only in the same commit as its fix; record the green workflow run and `headSha`.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_flow_gitignore test_gate_receipt test_reveval_parse_guard -q
```

## Acceptance
- [ ] A pre-fix current-HEAD Windows run characterizes all six files with current corpus count, test names/counts, tracebacks, elapsed time, exits, and child-process observations.
- [ ] Permanent `workflow_dispatch` inputs reproduce parallel/serial/shuffle or one-file verbose bounded runs on an exact ref; run evidence records `headSha`.
- [ ] Controlled text I/O is explicit UTF-8; the en-dash roundtrip passes on Windows without locale fallback.
- [ ] Only the impossible literal-backslash filename premise is POSIX-skipped; TTL/receipt behavior uses a proven seam/executable and asserts the delayed/failing double ran.
- [ ] Reveval guard resolves repo paths portably and its real subprocess path passes on Windows.
- [ ] All three files are removed from `EXCLUDES` in the same commit as fixes/regressions.
- [ ] Focused and combined `windows-latest` runs are green and their run URL/ID plus `headSha` is recorded in task evidence.
- [ ] Linux/macOS focused regressions remain green; no assertion is weakened.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
