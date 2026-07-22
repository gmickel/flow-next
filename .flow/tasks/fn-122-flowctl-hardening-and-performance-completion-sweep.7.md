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
Consolidated cognitive-aid diff processing into one materialized unified-diff event stream shared by cross-module, public-export, changed-symbol, and removed-reference analyses. Replaced whole-tree glossary walks and per-file `git show` calls with changed name-status candidates plus one strict UTF-8 `git cat-file --batch` read; removed the obsolete walker helpers and unused analysis arguments. Preserved rename/delete/re-add/protected-path semantics and current full-export bytes. Same live fn-122 fixture improved from 0.51 s median (0.50-0.52) to 0.38 s (0.38-0.38), 25.5% faster across five runs.
## Evidence
- Commits: f5186a88, d930c9fd
- Tests: cd plugins/flow-next/tests && PATH=/opt/homebrew/bin:$PATH PYTHON_BIN=/opt/homebrew/bin/python3 /opt/homebrew/bin/python3 -m unittest test_export_traceability test_export_cognitive_aid test_glossary test_qa_smoke test_startup_bootstrap -q (57 tests), pre/post full export SHA-256 equality on fn-122 against origin/main, canonical/dogfood flowctl.py cmp parity, git diff --check, flowctl codex impl-review round 2: SHIP
- PRs: