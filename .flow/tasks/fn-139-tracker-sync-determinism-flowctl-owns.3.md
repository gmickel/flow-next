---
satisfies: [R3, R24, R27, R31]
---
# fn-139-tracker-sync-determinism-flowctl-owns.3 Spec-aware status verb: fn-66 evidence gate + who-wins ladder

## Description
Implement `tracker status <spec-id> --to <normalized>`, which **embeds fn-66's merge-evidence gate** rather than forwarding the caller's requested status: terminal `Done` only on a GitHub-confirmed MERGED, `In Review` on an open PR, never terminal from completion-review alone.

Port the who-wins ladder **preserving branch order** - collision cases first. Memory `who-wins-ladder-must-check-the-...` records that reordering lets an earlier rule silently win. Enumerate deterministic outcomes for deadlock fallback and unmapped states; anything genuinely ambiguous returns `class: conflict` and routes to the skill's recovery surface (R12) rather than defaulting silently.

Jira status uses the cached transition id (one request, not discover-then-transition). GitHub's `duplicate` state reason is reachable via `--reason`.

## Acceptance
- [ ] A completion-review-only path cannot produce terminal Done
- [ ] Collision branches evaluate before single-field rules; a reordering test fails
- [ ] Jira status write is ONE request with a warm cache
- [ ] Unmapped/deadlock states return `class: conflict`, never a silent default
- [ ] `--reason duplicate` reachable on GitHub
- [ ] Receipt is event-tagged

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
