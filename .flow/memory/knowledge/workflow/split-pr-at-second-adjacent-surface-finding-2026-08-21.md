---
track: knowledge
category: workflow
module: review
tags: [resolve-pr, land, scope, review-rounds, pr-hygiene]
status: active
---

# Split the PR at the SECOND adjacent-surface finding, not the fifth

PR #363 (a two-closer prose feature) had 6 review rounds / 8 findings — all real,
zero churn. Rounds 3-5 were entirely an ADJACENT subsystem (installed-Codex docs
distribution) that the feature's single new docs link exposed: docs never installed,
then a destructive-install P1 introduced by our own round-3 fix, then link-closure
work. The split into its own PR was flagged at round 5; it should have happened at
round 3 — the moment a SECOND substantive finding landed in the same adjacent
surface rather than the PR's feature.

## How to apply

- Track which surface each review finding targets. Two substantive findings in the
  same surface that is not the PR's feature ⇒ propose splitting that surface into
  its own PR and restoring the original scope, BEFORE dispatching the next resolver.
- Rationale: each adjacent fix widens the review target and invites the next
  deeper finding (convergent residue); the class terminates fastest in a dedicated
  PR with its own closure guard, while the feature PR merges on its own merits.
- Counterweight: if the adjacent defect is a P1 the PR itself introduced, fix it
  in-PR regardless (never ship a known destructive regression), then split the rest.
