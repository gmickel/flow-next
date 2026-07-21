---
satisfies: [R12, R18]
---
# fn-122-flowctl-hardening-and-performance-completion-sweep.7 Cognitive-aid diff and glossary performance pass

## Description
Make export-cognitive-aid materialize and parse its unified diff once for summary, symbol/export, and removed-reference analyses. Derive glossary candidates from changed paths rather than walking both complete trees; batch base-object reads where multiple changed glossaries remain.

Preserve rename/deletion handling, same-file re-add suppression, protected paths, R-ID coverage, output ordering, and error behavior. Pin subprocess counts and byte-equivalent payloads across semantic fixtures.

Complexity: 64/100.

Quick commands:
- cd plugins/flow-next/tests && python3 -m unittest test_export_traceability test_export_cognitive_aid test_glossary -q
## Acceptance
- [ ] One unified-diff subprocess/event stream serves all diff-derived analyses.
- [ ] Glossary analysis examines changed candidate paths only and avoids per-unchanged-file git show calls.
- [ ] Add/delete/rename/re-add/protected-path fixtures produce byte-equivalent payloads.
- [ ] Deterministic subprocess/materialization budgets are asserted.
- [ ] Same-fixture pre/post benchmark evidence is recorded.
- [ ] Focused export/glossary suites pass.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
