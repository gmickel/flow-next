---
satisfies: [R2, R4, R19, R30, R32, R33]
---
# fn-139-tracker-sync-determinism-flowctl-owns.1 Adapter package skeleton, injected executor, tracker.resolved cache

## Description
Create `plugins/flow-next/scripts/tracker/` with one module per adapter over a shared typed transport/result layer, plus the **injected request executor** that every adapter calls instead of `subprocess.run` directly. That seam is the fake transport the whole test strategy depends on, so it lands here, not in .6.

Implement the `tracker.resolved` cache: destination + capabilities + `resolvedAt`, written atomically via the existing `atomic_write_json` and guarded by `cross_process_lock` (both already in flowctl.py). Implement the R4 state-transition table in full - absent block, absent field, stale value, capability up/downgrade, ambiguous Linear state, auth failure, retry exhaustion - with `--scope` for scoped re-resolution.

Migrate existing `perTracker.apiVersion: 3` configs to 2 (R30) rather than orphaning them.

`flowctl.py` gains argparse wiring only. No adapter logic in that file.

## Acceptance
- [ ] `scripts/tracker/` package exists; adapters call the injected executor, never subprocess directly
- [ ] `tracker.resolved` writes are atomic AND lock-protected; concurrent resolve produces no torn or clobbered cache (test with two processes)
- [ ] Every row of the R4 table has a test, including that an absent block returns `class: unresolved` and NOT a false capability `false`
- [ ] A transient 403 on the GitLab tier probe does NOT flip a capability
- [ ] `--scope` re-resolves only the named sub-map (a rejected Jira transition does not force full re-resolution)
- [ ] Existing `apiVersion: 3` config migrates to 2
- [ ] Secrets never written into `tracker.resolved`, never logged

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
