---
satisfies: [R14, R15]
---
# fn-141-tracker-determinism-c-prose-teardown.5 Re-freeze fn-130 tracker baselines with enumerated fixtures + delta

## Description
**Do NOT re-freeze B1.** `freeze_b1()` refuses a non-empty destination because B1 is write-once and hash-addressed; overwriting it destroys the provenance the delta is measured against. fn-134 updated **candidate** evidence, not B1 - follow that precedent.

Record the reduction as a **candidate delta**, naming every affected tracker fixture explicitly. If a genuinely new baseline is wanted, that is a deliberate **B2** with its own commit/tag, inventory constant, validator, lineage and migration rationale - never an in-place overwrite.

Runs after the canonical skill and caller edits (.2) and their behavioral verification (.3), so it never measures an intermediate tree or races generated mirror edits.

## Acceptance
- [ ] B1 left untouched; reduction recorded as a CANDIDATE delta
- [ ] Every affected tracker fixture enumerated by name
- [ ] Before/after delta recorded as an artifact
- [ ] Rationale recorded: reduction by design, not regression
- [ ] If a B2 is introduced instead, it carries commit/tag, inventory constant, validator and lineage
- [ ] Reached-path harness green
- [ ] sync-codex.sh run twice, mirror committed

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
