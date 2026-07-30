---
satisfies: [R5]
---
# fn-136-structured-review-artifact-schema-in.5 Docs, consumer contract, full gate

## Description
Document the complete portable findings contract and run the original findings stream's final gates.

**Size:** S

### Approach
- Document schema version, canonical enums/aliases, durable IDs, anchor semantics, receipt/round lineage, stale/current selection, deterministic order, limits and fallback behavior.
- Keep consumer wording product-neutral: stable receipts, never internal APIs.
- Update STRATEGY/GLOSSARY and Unreleased CHANGELOG as originally planned, without a version bump.
- Run sync-codex twice, focused suites, full tests and pinned Ruff.
## Acceptance
- [ ] Receipt/memory/consumer docs define versioning, enums, anchors, lineage/currentness, bounds and fallback behavior (R5).
- [ ] Strategy/glossary/Unreleased entries are present; mirrors are idempotent; full gates pass.
## Done summary
Documented and regression-pinned the complete portable structured-findings contract, including receipt-envelope bindings, exact SHA-256 finding IDs, and bound versus unbound range behavior. Updated the public receipts documentation, passed focused/full/Ruff/Astro gates, and obtained RepoPrompt SHIP in the required same CE chat.
## Evidence
- Commits: d2c12672de6691a9f41f9b16024db631adcfaff0, f8b74fe4f4411c19d35621b93aeece376f343f4a, 89a001c8867a120727047b52556f287e24ef9220, c6fdeb03b975248d129d7969e80f0debf89876a1, 7d78fa81b43530d90e87abb435349667251cce1f, 3ceb826beb4b158850a8f0492ffc80def0481663, c0a08e5b236cee27e3d015fc6e1438e0b1c7828f
- Tests: python3 -m unittest plugins.flow-next.tests.test_review_findings_docs plugins.flow-next.tests.test_review_findings_parser plugins.flow-next.tests.test_review_findings_receipts -q (67 tests, OK), ./scripts/sync-codex.sh (twice, exit 0; idempotent), python3 scripts/run_tests_parallel.py (3397 tests, 0 failures, 0 errors, 4 skipped), uvx ruff@0.16.0 check . (All checks passed), flow-next.dev: ./node_modules/.bin/astro check (0 errors/warnings/hints), flow-next.dev: ./node_modules/.bin/astro build (76 pages), GATE_SKIPPED:unittest:green-receipt 7d78fa81 - baseline reused from prior post-gate pass
- PRs: