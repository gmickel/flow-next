---
satisfies: [R1]
---
# fn-138-published-json-schema-for-flow-config.1 Schema generator + committed artifact

## Description
Deterministic generator + byte-stable committed schema.

**Size:** M

**Files:** new generator (scripts/ or flowctl subcommand - pick per repo convention; pure stdlib), committed artifact at plugins/flow-next/schema/flow-config.schema.json, regen test.

### Approach
- One structured table (key path -> type/enum/pattern/description) as the single source; descriptions lifted from flowctl.md config docs. Survey the CURRENT surface at implementation time (~44 dotted keys as of 3.11.0): the review-backend spec grammar backend[:model[:effort]] as a pattern, pipeline.qa, work.delegate*, artifacts.html.*, the full tracker.* block incl. the fn-139 `tracker.resolved` destination/capability cache (atomic, partially-absent-by-design - schema must tolerate absence) and `tracker.conflictTiebreak` (fn-146), models.roles.*/verifiedAt/verifiedWith (fn-115), land.* incl. cleanReviewCommentPattern (empty-string-means-disabled contract), pilot.autonomy/gateClasses. flowctl.md § config is authoritative; the .2 drift guard is the honesty mechanism.
- Emit draft 2020-12; deterministic ordering; regen test asserts byte-identity (the fn-113 evidence pattern).

## Acceptance
- [ ] Generator + committed artifact byte-stable w/ regen test; full documented surface covered (R1).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
