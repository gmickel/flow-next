---
satisfies: [R8, R9, R12]
---
# fn-120-windows-test-corpus-compatibility-sweep.4 Prove final zero-exclusion Windows corpus matrix

## Description
Prove the final zero-exclusion corpus in parallel, serial, and shuffled modes across the supported OS matrix and record the compatibility result.

**Size:** M
**Files:** .github/workflows/test-flow-next.yml only if final proof exposes a matrix bug, scripts/run_tests_parallel.py only if proof exposes an order-mode bug, CHANGELOG.md

### Approach

On the exact final candidate SHA, run `windows-latest` through the permanent workflow-dispatch inputs in full parallel, full serial, and shuffled/order-varied modes. Require zero workflow-filtered files. Run Linux and macOS full gates on the same SHA. Record every run URL/ID and `headSha`, remove temporary probes, retain the permanent bounded diagnostic inputs, and add an `## Unreleased` changelog entry with no version bump.

### Quick commands

```bash
python3 scripts/run_tests_parallel.py
python3 scripts/run_tests_parallel.py --serial
python3 scripts/run_tests_parallel.py --shuffle --seed 120
```

## Acceptance
- [ ] Exact-SHA Windows full parallel, full serial, and shuffled/order-varied runs pass with zero workflow-filtered files.
- [ ] Linux and macOS full gates pass on the same final SHA.
- [ ] Every proof records workflow URL/ID plus `headSha`; run heads match the candidate commit.
- [ ] Workflow contains no Windows `EXCLUDES` block and runner list-only confirms the complete current corpus.
- [ ] Temporary diagnostics are removed; permanent manual diagnostic inputs and bounded cleanup diagnostics remain.
- [ ] CHANGELOG contains an `## Unreleased` Windows corpus parity entry; no version manifest or public docs change.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
