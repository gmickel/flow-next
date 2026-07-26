---
satisfies: [R1, R2, R3]
---

# fn-139-tracker-determinism-a-transport.1 Distribution: ship flowctl_tracker/ on every runtime
# fn-139-tracker-sync-determinism-flowctl-owns.1 Adapter package skeleton, injected executor, tracker.resolved cache

## Description
Split adapters into a namespaced `flowctl_tracker/` package and make it ship everywhere flowctl does.

Distribution today enumerates files by name: `install-codex.sh:245-251` copies exactly `flowctl` and `flowctl.py`; copy-mode setup writes a fixed list into `.flow/bin/`; Ralph scaffolding does the same. Cursor is free (`install-cursor.sh:72` is a blanket `rsync -a --delete` with excludes).

`SOURCE_SHA256` at `flowctl_bootstrap.py:20` pins exactly one file and must become a manifest over every distributed file.

Namespaced, never a bare `tracker/` - the package lands on `sys.path` and a generic name invites collisions.

## Acceptance
- [ ] Package ships via plugin mode, copy-mode `.flow/bin`, install-codex.sh, install-cursor.sh, Ralph scaffolding
- [ ] Per-runtime import smoke test fails at INSTALL time, not on first tracker op
- [ ] `SOURCE_SHA256` is a manifest; a partially-copied package fails the integrity check
- [ ] Every test loading flowctl via `spec_from_file_location` has `scripts/` on sys.path
- [ ] Windows: `flowctl.cmd` path verified with the package present

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
