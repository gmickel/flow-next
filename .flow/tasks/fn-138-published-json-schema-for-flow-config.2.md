---
satisfies: [R2, R4]
---
# fn-138-published-json-schema-for-flow-config.2 Reader-schema drift test + fixture validation

## Description
Both-directions honesty between the config reader and the schema; fixture validation.

**Size:** M

### Approach
- Drift test: enumerate reader-accepted keys (walk flowctl.py config access sites - build the inventory mechanically where feasible, else a maintained list WITH a guard that greps config.get sites and fails on uncounted additions); assert reader-keys == schema-keys both directions.
- Fixture configs valid + invalid (bad enum, bad spec-grammar, unknown key behavior documented) validated with a small stdlib structural checker (no new deps).

## Acceptance
- [ ] Drift test fails on either-direction divergence (R2).
- [ ] Fixture validation stdlib-only (R4).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
