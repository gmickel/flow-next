---
satisfies: [R12, R13, R14, R16]
---
# fn-140-tracker-determinism-b-verb-surface.5 sync-body: readback canonical, paired merge base transaction

## Description
Implement `tracker sync-body <spec-id>`: write, read back, seed the paired merge base - **one transaction**.

**Server readback is canonical.** The merge base comes from what the tracker returns, never what we sent. Measured: Linear rewrites descriptions six ways (`_italic_`->`*italic*`, `[l](url)`->`[l](<url>)`, `- `->`* `, table separators, `[x]`->`[X]`, trailing newline); GitLab strips the trailing newline. Client normalization is limited to trailing-newline and does NOT predict Linear's rewriting - unsafe around code fences and unnecessary given readback.

Preserve the paired-snapshot invariant (memory `paired-snapshot-setter-must-write-both`): both halves at one sync point, atomically, never per-flag.

Jira body ops use apiVersion 2 (plain string round-trips byte-exact). Comment sync filters GitLab system notes.

## Acceptance
- [ ] No-op reconcile against an unmodified issue produces NO diff on all four
- [ ] Merge base equals the readback, not the sent body
- [ ] Partial failure leaves the prior merge base untouched
- [ ] Jira v2 plain-string body round-trips byte-exact
- [ ] GitLab `system: true` notes filtered
- [ ] No client-side attempt to predict Linear's rewriting

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
