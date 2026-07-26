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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
