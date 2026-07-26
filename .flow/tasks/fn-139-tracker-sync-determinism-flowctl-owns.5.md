---
satisfies: [R7, R8, R9, R26]
---
# fn-139-tracker-sync-determinism-flowctl-owns.5 Body sync: server readback canonical, paired merge base as one transaction

## Description
Implement `tracker sync-body <spec-id>`: write, read back, and seed the paired merge base as **one transaction**.

**Server readback is canonical** - the merge base comes from what the tracker returns, never from what we sent. Client normalization is limited to an enumerated set of stable transformations (trailing-newline stripping); it does NOT attempt to predict Linear's markdown rewriting, which is unsafe around code fences and escapes and is unnecessary given readback.

Preserve the paired-snapshot invariant (memory `paired-snapshot-setter-must-write-both`): both halves at one sync point, atomically, never per-flag. Jira body ops use apiVersion 2 (plain string round-trips byte-exact; Jira converts to ADF for v3 readers itself). Comment sync filters GitLab system notes (`system: true`).

## Acceptance
- [ ] A no-op reconcile against an unmodified issue produces NO diff on all four adapters
- [ ] Merge base equals the readback, not the sent body
- [ ] Partial failure leaves the prior merge base untouched (test)
- [ ] Jira v2 plain-string body round-trips byte-exact
- [ ] GitLab system notes filtered from comment sync
- [ ] No client-side attempt to predict Linear's rewriting

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
