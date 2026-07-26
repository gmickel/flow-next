---
satisfies: [R1, R2, R15]
---
# fn-139-tracker-determinism-a-transport.5 Distribution finalization: manifest, installer verification, runtime smokes

## Description
Finalize distribution **last**, once .1-.4 have added every file a manifest must cover.

Integrity is verified **where it can actually run**. `flowctl_bootstrap.py` executes only for a bare `usage` / `--help` (`flowctl:44-48`); every ordinary command execs `flowctl.py` directly, so today a hash mismatch merely disables the help fast path and fails nothing. Therefore: **installers verify the manifest after copying** and fail loudly there (`install-codex.sh:245-251` enumerates files by name; copy-mode setup and Ralph scaffolding do the same; `install-cursor.sh:72` is a blanket rsync and needs no enumeration change), plus a CI packaging smoke.

Marketplace/plugin installs have no plan-controlled post-install hook, so those fail on **first invocation** with a clear integrity error rather than a silent fallback.

Per-command hashing is explicitly rejected: it would tax every invocation to catch what installers already cover.

Finally, assert the bridge-inactive path is byte-for-byte unchanged with the package present.

## Acceptance
- [ ] Manifest enumerates its members explicitly
- [ ] Each installer verifies post-copy and FAILS loudly on mismatch
- [ ] Marketplace/plugin mode fails on first invocation with a clear integrity error, never a silent fallback
- [ ] CI packaging smoke covers every runtime incl. Windows `flowctl.cmd`
- [ ] Bridge-inactive path byte-for-byte unchanged with the package present (reached-path harness)
- [ ] No per-command hashing added

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
