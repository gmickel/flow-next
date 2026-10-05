# Maintainability pointer (gated reference)

> Read from SKILL.md only when the verdict's `maintainability:` block names a finding.

**Maintainability pointer.** The verdict's `maintainability:` block is
advisory and lives in the verdict artifact. When either key names a finding
(anything other than `none identified`), append one line to the current
spec's `## Decision Context` with `spec set-plan` in the round the finding
arrived, whatever the verdict: `Maintainability (plan review): duplication -
<finding or none identified>; structure - <finding or none identified>`. Both
keys `none identified` writes nothing; a verdict without the block reads as
"not asked", never as "no risk". No new section, no new flag. On a `SHIP`
round that write reports `plan_review_stale: true`; the line records the review
that just shipped, so restore it with
`$FLOWCTL spec set-plan-review-status <SPEC_ID> --status ship --json`.
