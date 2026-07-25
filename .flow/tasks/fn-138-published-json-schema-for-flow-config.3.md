---
satisfies: [R3, R5]
---
# fn-138-published-json-schema-for-flow-config.3 Setup schema stamping + docs

## Description
$schema stamping + documentation + convergence.

**Size:** S

### Approach
- Setup writes `$schema` (stable flow-next.dev URL) into configs it scaffolds/refreshes; existing configs untouched otherwise; both setup modes honored.
- Docs: flowctl.md config section links the schema; Unreleased CHANGELOG; downstream-walk note lists the docs-site publication of the schema file at the stable URL.
- Full suite + smoke where touched.

## Acceptance
- [ ] Stamping on scaffold/refresh only; docs + Unreleased + walk note; full gate green (R3, R5).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
