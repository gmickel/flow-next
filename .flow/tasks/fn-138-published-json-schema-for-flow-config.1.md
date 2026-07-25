---
satisfies: [R1]
---
# fn-138-published-json-schema-for-flow-config.1 Schema generator + committed artifact

## Description
Deterministic generator + byte-stable committed schema.

**Size:** M

**Files:** new generator (scripts/ or flowctl subcommand - pick per repo convention; pure stdlib), committed artifact at plugins/flow-next/schema/flow-config.schema.json, regen test.

### Approach
- One structured table (key path -> type/enum/pattern/description) as the single source; descriptions lifted from flowctl.md config docs (survey the ~39 documented keys + the review-backend spec grammar backend[:model[:effort]] as a pattern, pipeline.qa, work.delegate*, artifacts.html.*, tracker.*).
- Emit draft 2020-12; deterministic ordering; regen test asserts byte-identity (the fn-113 evidence pattern).

## Acceptance
- [ ] Generator + committed artifact byte-stable w/ regen test; full documented surface covered (R1).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
