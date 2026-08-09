# Sibling-identity warning on claim reclaim

**Decision:** No identity-legitimacy heuristics on `flowctl start` claim reclaim/takeover.

Which claimant identities are legitimate is governance that belongs to the consuming
repo, not flowctl: a warning heuristic (flag reclaims across sibling identities)
guesses at policy it cannot know and trains users to ignore it when it guesses wrong.
The record-integrity half of #316 (a repair-flavored claim note distinct from `--force`
takeover) is in scope for fn-179; the heuristic half stays out.

## Prior requests
- 2026-08-08 - issue #316 (sn-furali) suggested an optional sibling-identity warning; dropped at fn-179 capture as heuristic creep.
