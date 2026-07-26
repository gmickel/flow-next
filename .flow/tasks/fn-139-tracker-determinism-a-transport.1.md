---
satisfies: [R3]
---

# fn-139-tracker-determinism-a-transport.1 Package skeleton + test sys.path sweep
# fn-139-tracker-sync-determinism-flowctl-owns.1 Adapter package skeleton, injected executor, tracker.resolved cache

## Description
Create the namespaced `flowctl_tracker/` package (never a bare `tracker/` - it lands on `sys.path`). Structure only; adapters arrive in later tasks.

**Sweep the test suite**: measured, **68 test modules load flowctl via `spec_from_file_location` and 63 lack a `sys.path.insert`**. Under those modules `sys.path[0]` is the *test* directory, not `scripts/`, so the package would not import under test even though it imports fine in production. This is mechanical but broad, which is why it owns its own task.

Manifest and integrity verification are deliberately NOT here - they land last, once .2-.4 have added the files a manifest must cover.

## Acceptance
- [ ] `flowctl_tracker/` exists, namespaced, importable from the repo checkout
- [ ] All 68 `spec_from_file_location` modules have `scripts/` on sys.path
- [ ] A trivial adapter stub imports under test AND under the real launcher from the checkout
- [ ] Copy-mode / installed-runtime import proof is NOT claimed here - it belongs to .5, which does the distribution work
- [ ] No manifest work in this task

## Done summary
Created the namespaced `flowctl_tracker/` package (structure only; executor is .2, adapters .4/.6) and made every test module that loads flowctl able to reach it.

The sweep: 68 modules load flowctl via `spec_from_file_location`. In production `sys.path[0]` is the launcher's directory so a sibling package imports naturally, but under a test module it is the tests directory, so 63 of them could not have reached the package. 47 were auto-patched; 16 first needed `import sys` / `from pathlib import Path`; `test_backend_spec.py` needed its insert placed before flowctl loads.

Deliberately NOT done here, per the task's own acceptance: no manifest, no integrity verification, no installer changes. Distribution is task .5, sequenced last so the manifest covers files that exist by then. The acceptance test therefore claims importability from the checkout only, not from an install.

Three impl-review rounds, and every finding was a TEST defect rather than a code defect: a guard matching any `sys.path.insert` (so it read 67/68 as 68); a replacement regex that could never match the canonical form because `[^)]*` stops at the `)` of `resolve()`; and a truthiness assertion masking a `__version__` that contradicted the manifests. The guard is now statement-scoped and mutation-tested, and `__version__` is gone rather than synced - a field that lies is worse than an absent one.
## Evidence
- Commits: 78c3c88a, 0fa1653a, 07dcc524
- Tests: python3 scripts/run_tests_parallel.py
- PRs: