---
satisfies: [R2]
---
# fn-181-state-provenance-status-source-review.2 Review-skill prose: committed task status is not authoritative

## Description
Spec fn-181 item 2 (#304 half 2, the load-bearing half). Plan-review + completion-review prose: committed .flow/tasks/<id>.json status is not authoritative; lifecycle lives in git-common-dir flow-state (unreachable from a diff-scoped sandbox); task lifecycle is not the reviewer's to judge (completion review = spec compliance only). One to two sentences per skill (fn-82 budget). sync-codex twice.

## Acceptance
R2 of the spec. Occurrence-3 shape (sidecar read while flow-state says done) is ruled out by prose a skill-following reviewer cannot miss.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
