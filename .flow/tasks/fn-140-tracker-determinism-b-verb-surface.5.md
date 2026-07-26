---
satisfies: [R12, R13, R14, R16]
---
# fn-140-tracker-determinism-b-verb-surface.5 sync-body: readback canonical, paired merge base transaction

## Description
Implement `tracker sync-body <spec-id>`: write, read back, seed the paired merge base - **one transaction**.

**The two halves differ**: `mergeBaseFlow` = the exact final local spec body (must stay comparable to the local spec); `mergeBaseTracker` = `trackerBodyForMerge(server readback)`. Storing the readback in both would make Linear's rewriting look like instant flow-side divergence.

`sync-body` takes `--flow-file` (and `--tracker-body-file` on a two-way reconcile) because flowctl never composes a merged body - that is the skill's judgment surface. `--direction pull` snapshots both forms without writing. Measured: Linear rewrites descriptions six ways (`_italic_`->`*italic*`, `[l](url)`->`[l](<url>)`, `- `->`* `, table separators, `[x]`->`[X]`, trailing newline); GitLab strips the trailing newline. Client normalization is limited to trailing-newline and does NOT predict Linear's rewriting - unsafe around code fences and unnecessary given readback.

Preserve the paired-snapshot invariant (memory `paired-snapshot-setter-must-write-both`): both halves at one sync point, atomically, never per-flag.

Jira body ops use apiVersion 2 (plain string round-trips byte-exact). Comment sync filters GitLab system notes.

## Acceptance
- [ ] No-op reconcile against an unmodified issue produces NO diff on all four
- [ ] `mergeBaseFlow` = local spec body; `mergeBaseTracker` = readback; both committed atomically after write+readback succeed
- [ ] `--direction pull` establishes a valid paired base without writing
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
