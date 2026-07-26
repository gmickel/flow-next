---
satisfies: [R6, R7]
---
# fn-141-tracker-determinism-c-prose-teardown.3 Verify inactive path + every perEvent value end to end

## Description
Verify the invariant this whole batch rests on, AFTER rewiring - because .2 is what changes the final inactive path.

Bridge-inactive: one config read, no adapter import, no new output, byte-for-byte unchanged. Asserted via the reached-path harness.

Then test every configured `perEvent` value end to end: `off | pull | push | reconcile | comment` - an earlier draft omitted **`pull`**. Enumerate every event key and its legal values, including QA's comment-only rule and land's unconditional status rule.

Instrument each caller with a **fake flowctl** and assert config reads, argv, imports, stdout and stderr against a **pre-teardown captured oracle**, so "byte-for-byte" names both the streams and the thing compared.

## Acceptance
- [ ] Bridge-inactive path byte-for-byte unchanged (reached-path harness)
- [ ] No adapter package import occurs on the inactive path
- [ ] Every perEvent value incl. `pull` tested end to end; QA comment-only and land unconditional-status rules covered
- [ ] Fake flowctl asserts config reads, argv, imports, stdout, stderr vs a pre-teardown oracle

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
