---
satisfies: [R3, R5]
---
# fn-138-published-json-schema-for-flow-config.3 Setup schema stamping + docs

## Description
$schema stamping + documentation + convergence.

**Size:** S

### Approach
- Setup writes `$schema` (stable URL `https://flow-next.dev/schema/flow-config.schema.json` - latest-mutable, not versioned) into configs it scaffolds/refreshes via the cmd_init write paths (_init_persisted_defaults on absent config; deep-merge rewrite on re-init); existing configs untouched otherwise; both setup modes honored; offline-tolerant (inert string, flowctl never fetches it).
- Docs: flowctl.md config section links the schema AND corrects the wrong default rows (memory.enabled, planSync.enabled - documented false, code default true); Unreleased CHANGELOG; downstream-walk note lists the docs-site publication of the schema file at the stable URL BEFORE the release announcement (until published, editors show a transient could-not-load-reference warning - accepted, noted in the CHANGELOG entry).
- Full suite + smoke where touched.

## Acceptance
- [ ] Stamping on scaffold/refresh only; docs + Unreleased + walk note; full gate green (R3, R5).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
