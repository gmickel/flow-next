---
satisfies: [R2]
---
# fn-166-flowctl-module-split-importable.4 Distribution integrity contract for flowctl_review (manifest + tests + installers)

## Description
Give `flowctl_review/` the same distribution integrity contract `flowctl_tracker/` has: generated MANIFEST, fail-closed installer verification, and a `test_tracker_distribution`-style integrity suite.

**Size:** M
**Files:** `scripts/gen_tracker_manifest.py` (generalize — preferred) or a sibling generator, `plugins/flow-next/scripts/flowctl_review/MANIFEST.json` + `.flow/bin/flowctl_review/MANIFEST.json`, `scripts/lib/verify_tracker_manifest.py`, NEW `plugins/flow-next/tests/test_review_distribution.py` (or parametrized extension), `scripts/install-codex.sh`, `scripts/install-cursor.sh`, `scripts/install-cursor.ps1`, `plugins/flow-next/skills/flow-next-setup/workflow.md`, `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md` (where verifier-invocation prose is test-asserted)

### Approach
- Prefer generalizing `gen_tracker_manifest.py` to N packages over hardcoding a second call — every future extraction repeats this otherwise. Keep `--check` mode; keep writing BOTH copies (scripts/ + .flow/bin/), mirroring lines 63-66 of the current generator.
- Integrity suite mirrors `test_tracker_distribution`: ManifestIsCurrent, InstallerVerifier (fail-closed on absent/tampered/missing manifest — the ExecutableInstallerFailClosed pattern with real installer runs), RuntimeSmoke (real launcher incl. `.cmd`). Tracker's BridgeInactiveByteParity has NO analog (review machinery has no inactive mode) — replace it with an absent-package soft-fail message test (message must name flowctl_review, not a bare traceback).
- Installers verify the new package exactly like flowctl_tracker; `test_tracker_distribution.py:115-125` asserts skill docs invoke the verifier — extend those assertions/prose for the new package.
- `flow-next-setup/workflow.md` copy steps gain the package (the remove-then-recopy shape at :140-151, same as the tracker package lines).

### Investigation targets
**Required** (read before coding):
- `scripts/gen_tracker_manifest.py:1-71` — generator to generalize
- `plugins/flow-next/tests/test_tracker_distribution.py` — the 326-line template (esp. :115-125 installer-prose assertions, :197-201 MANIFEST.json string ban)
- `scripts/lib/verify_tracker_manifest.py` — shared verifier

**Optional** (reference as needed):
- `scripts/install-codex.sh`, `scripts/install-cursor.sh`, `scripts/install-cursor.ps1` — verifier call sites
- `plugins/flow-next/skills/flow-next-setup/workflow.md:140-151` — propagation prose

### Key context
- The "MANIFEST.json" literal stays OUT of flowctl.py (generator/installer/tests only).
- Codex mirror carries no Python source — expect zero `plugins/flow-next/codex/` diff; still run `./scripts/sync-codex.sh` twice at the gate (idempotency; memory lesson: audit sync-codex.sh whenever scripts/ changes).

## Acceptance
- [ ] `flowctl_review/MANIFEST.json` generated + propagated to both copies; `--check` mode works
- [ ] New integrity suite green: manifest-current, fail-closed installers (absent/tampered/missing), runtime smoke, absent-package message
- [ ] Installers + setup/ralph-init prose verify the new package, with test assertions matching the tracker equivalents
- [ ] `test_tracker_distribution` still fully green (no regression to the tracker contract)

## Done summary
NOT IMPLEMENTED — closed as superseded, 2026-08-13.

This task's work moved in the fn-166 split: launcher + verdict-map work to `fn-190-flowctl-startup-importable-entry-for`, package extraction + distribution integrity to `fn-191-flowctl-review-terminal-machinery`. No code, docs, or tests were produced here; `done` is a lifecycle marker so the parent spec could be closed (`spec close` requires done tasks and flowctl has no supersede terminal). Read the successors.
## Evidence
- Commits:
- Tests:
- PRs: