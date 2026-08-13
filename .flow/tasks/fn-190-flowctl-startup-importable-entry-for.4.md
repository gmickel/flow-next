---
satisfies: [R7]
---
# fn-190-flowctl-startup-importable-entry-for.4 Route the unit suite's flowctl invocations through the entry

## Description
Point the unit suite's flowctl invocations at the entry so the local gate actually collects the saving. Measured on the spike: a representative memory test went 1.586s -> 0.922s (-42%) purely by resolving flowctl through the entry. Without this task the wrapper is faster but the suite is not, because tests spawn the module directly through their own per-file constant.

**Size:** S/M (mechanical, but wide: ~74 files define the constant)
**Files:** `plugins/flow-next/tests/*.py` (the per-file `FLOWCTL_PY` constants); a shared helper if one is warranted
**Touches:** [plugins/flow-next/tests/**]

### Approach
- The constant appears in ~74 test files as `FLOWCTL_PY = HERE.parent.parent / "scripts" / "flowctl.py"` (re-grep for the exact spelling; some files differ). Prefer introducing ONE shared resolver the tests import over 74 independent edits - fewer places for the next change to miss - but do not restructure the test tree to get it.
- **Deliberate exceptions, keep pointing at the source script and say so in a comment:** tests that assert on the bootstrap/static-help path, launcher parity, init restamping, or the manifest source hash. Those exist to cover the direct-invocation contract; routing them through the entry would test the wrong thing.
- Measure before/after wall for the two spawn-heaviest files (~181 and ~168 flowctl spawns for 69 and 53 tests) and for the whole suite via the parallel entrypoint. Report the suite number honestly: wall is set by the slowest file at 14 jobs, so the total moves less than the per-file numbers suggest.
- Do not weaken or reshape any assertion. This task changes how tests reach the CLI, never what they assert (G2).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/tests/test_memory_core.py` - the constant's canonical spelling and how helpers consume it
- `plugins/flow-next/tests/test_startup_bootstrap.py`, `test_bin_launcher_parity.py`, `test_init_stamp_launchers.py` - the deliberate exceptions

### Key context
- A test that gets FASTER but also gets EASIER has been broken, not optimized - the assertion set must be identical before and after.

## Acceptance
- [ ] Suite invocations resolve flowctl through the entry (shared resolver preferred over per-file edits); assertion set unchanged
- [ ] Bootstrap / launcher-parity / init-restamp / manifest-hash tests still invoke the source script directly, each with a comment saying why
- [ ] Before/after wall recorded for the two spawn-heaviest test files and for the full parallel suite; the suite number reported with the slowest-file bound stated
- [ ] Full suite green (`python3 scripts/run_tests_parallel.py`, exit code captured directly) + `uvx ruff@0.16.0 check .`


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
