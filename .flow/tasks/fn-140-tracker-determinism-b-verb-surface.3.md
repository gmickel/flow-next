---
satisfies: [R6, R7, R8]
---
# fn-140-tracker-determinism-b-verb-surface.3 status verb: fn-66 evidence gate + who-wins ladder

## Description
Implement `tracker status <spec-id> --to <normalized>`, embedding **fn-66's merge-evidence gate** rather than forwarding the caller's request: terminal `Done` only on a GitHub-confirmed MERGED, `In Review` on an open PR, never terminal from completion-review alone.

Port the who-wins ladder **preserving branch order** - collision cases first. Memory `who-wins-ladder-must-check-the-...` records that reordering lets an earlier rule silently win. Enumerate deterministic outcomes for deadlock fallback and unmapped states; genuinely ambiguous cases return `class: conflict` for the skill's recovery surface.

Jira uses the cached transition id: one request, not discover-then-transition (status cannot be set via fields - measured 400). GitHub's undocumented `duplicate` reason is reachable via `--reason`.

## Acceptance
- [ ] Completion-review alone cannot produce terminal Done
- [ ] Collision branches evaluate before single-field rules; a reordering test fails
- [ ] Jira status write is ONE request with a warm cache
- [ ] Unmapped/deadlock states return `class: conflict`, never a silent default
- [ ] `--reason duplicate` reachable on GitHub; garbage reason 422s
- [ ] GitLab states handled as `opened`/`closed`

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
