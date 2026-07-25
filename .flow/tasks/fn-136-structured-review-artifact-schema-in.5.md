---
satisfies: [R5]
---
# fn-136-structured-review-artifact-schema-in.5 Docs, consumer contract, full gate

## Description
Document the findings contract; converge.

**Size:** S

### Approach
- Docs: memory-schema/receipts pages gain the findings schema + consumer notes; a short consumer contract section (field semantics, degrade behavior, versioning stance: additive-only).
- REPO SELF-CONTEXT: STRATEGY.md gains a 'downstream consumers' track note (flow-next emits structured machine-readable evidence - findings today, criteria compliance and config schema alongside - consumed by cockpit-class tools; receipts are the stable contract, never internal APIs) and GLOSSARY.md gains 'structured findings'; wording stays product-neutral pending the naming decision (see spec-prose note).
- Unreleased CHANGELOG entry (repo + note for the docs-site walk); NO version bump (batched).
- FULL suite: python3 scripts/run_tests_parallel.py + bash smoke where touched.

## Acceptance
- [ ] Docs + consumer contract + Unreleased entries; full suite green (R5).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
