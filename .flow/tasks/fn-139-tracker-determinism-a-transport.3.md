---
satisfies: [R8, R10, R12, R13]
---

# fn-139-tracker-determinism-a-transport.3 tracker.resolved cache: atomic writes, state table, migration
# fn-139-tracker-sync-determinism-flowctl-owns.3 Spec-aware status verb: fn-66 evidence gate + who-wins ladder

## Description
Implement the `tracker.resolved` block and its full state-transition table.

Writes are atomic (`atomic_write_json`) and lock-protected (`cross_process_lock`) - both primitives already exist in flowctl.py. A partially-resolved block is never stamped with a `resolvedAt` that would make it look warm to consumers.

Implement `--scope` so a rejected Jira transition refreshes the transitions sub-map, not the whole destination block. Migrate existing `perTracker.apiVersion: 3` configs to 2.

The capability re-probe is synchronous and bounded, not a background process: no daemon, no lifecycle, and a failed probe leaves the prior capability and reports it.

## Acceptance
- [ ] Two concurrent resolves produce no torn or clobbered cache (two-process test)
- [ ] Every row of the state table has a test
- [ ] Absent block yields `class: unresolved`, NOT a false capability `false`
- [ ] Transient 403 on the tier probe does not flip a capability
- [ ] `--scope` refreshes only the named sub-map
- [ ] `apiVersion: 3` migrates to 2
- [ ] Partial resolution never stamps `resolvedAt`

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
