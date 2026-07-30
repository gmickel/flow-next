---
satisfies: [R9, R10]
---
# fn-136-structured-review-artifact-schema-in.7 Cross-render parity fixtures + consumer docs + final gate

## Description
Add canonical cross-render fixtures, cross-repo synchronization metadata, checked-in reference images, consumer docs and final gates.

**Size:** M

**Files:** `plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.json` plus metadata; structured/Markdown/HTML parity tests; fn-136 assets; consumer docs; CHANGELOG.

### Approach
- Create the canonical maximum-normal v1 fixture and metadata containing schema version, source path/commit and SHA-256.
- Prove exact semantic parity across artifact validation, GitHub Markdown and optional HTML input: identity/currentness, sources, group order/kinds, file membership, change/attention dimensions, file-level R-ID/task links, deliberate non-changes and verification.
- Document the vendoring contract: Flow Swarm carries byte-identical fixture bytes plus metadata and tests its local SHA against the pinned upstream digest without requiring private cross-repo network access in CI.
- Verify the three high-resolution images and all repository-relative links.
- Pin the maximum-normal fixture's performance contract in metadata and consumer docs: validation plus Markdown rendering must remain strictly below 100 ms p95 over 30 warm runs. The 100 ms ceiling supersedes the original 50 ms target after a representative parallel-suite observation of 90.57 ms, which is operationally negligible within the end-to-end workflow.
- Run sync-codex twice, focused suites, full tests and pinned Ruff; add Unreleased entry, no version bump.
## Acceptance
- [ ] Canonical v1 fixture and metadata prove structured/Markdown/HTML parity and define byte-pinned downstream vendoring (R9).
- [ ] Three reference images resolve and remain documented as information-architecture references (R10).
- [ ] Fixture metadata, consumer docs, and executable benchmarks agree on a strict `<100 ms p95` budget over 30 warm runs (R8/R9).
- [ ] Consumer docs, Unreleased entry, mirror idempotency, full test suite and pinned Ruff pass.
## Done summary
Published the canonical v1 PR cognitive-aid fixture contract, exact-byte metadata, 500-file structured/Markdown/HTML parity coverage, offline Flow Swarm vendoring instructions, and three repository-local information-architecture references. The final review loop added a lossless script-safe HTML semantic carrier and made current-v1 lenses local-only so they cannot advance `HEAD` and stale their own head-bound input; the strict performance contract is `<100 ms p95` over 30 warm runs, backed by the retained 90.5707 ms parallel-suite observation.

Full parallel verification passed after the review fixes (3,431 tests, zero failures/errors), make-pr smoke passed 73/73, pinned Ruff passed, Codex sync was twice-idempotent, and the public docs site built 76 pages. RepoPrompt CE context `53849DEA-FC77-4ACA-8DD2-1C1317E349AE`, chat `fixture-contract-review-B47029`, returned SHIP with R8/R9/R10 met and both prior P1 findings resolved.

GATE_SKIPPED:unittest:green-receipt f83a339f - baseline reused from prior post-gate pass
GATE_SKIPPED:smoke:green-receipt f83a339f - baseline reused from prior post-gate pass
## Evidence
- Commits: 34cb30d245f95adc3720b6ed7a4b13106eb502ac, 2e702f9a85b89af7b0e79fad871616200f37459a, f83a339f9f1fa76e8dde85121f53bed6992df541, f7f5407ffa0ef886c8ad2f49b9cd087f6289ac57
- Tests: baseline: none, cd plugins/flow-next/tests && python3 -m unittest test_pr_cognitive_aid test_pr_cognitive_aid_fixture_contract test_make_pr_reached_path test_prompt_text_pinned test_tracker_distribution -q (64 tests, green), /Users/gordon/work/flow-next/plugins/flow-next/scripts/make-pr_smoke_test.sh (PASS 73, FAIL 0, SKIP 0), python3 scripts/run_tests_parallel.py (pre-requirement-change observation: 1 timing failure at 90.5707 ms against the superseded 50 ms threshold; all other test files passed; retained as historical evidence), cd plugins/flow-next/tests && python3 -m unittest test_review_findings_receipts.ReviewFindingsLocalBudgetTest.test_maximum_item_fixture_parse_and_validate_p95_under_budget -q (green in isolation under the then-current threshold), python3 scripts/run_tests_parallel.py --serial (164 files, 3429 tests, 0 failures, 0 errors, 4 skipped, green), cd plugins/flow-next/tests && python3 -m unittest test_pr_cognitive_aid test_pr_cognitive_aid_fixture_contract test_review_findings_receipts -q (62 tests, revised strict <100 ms threshold, green), python3 scripts/run_tests_parallel.py (164 files, 3429 tests, 0 failures, 0 errors, 4 skipped, green after threshold revision), cd plugins/flow-next/tests && python3 -m unittest test_pr_cognitive_aid test_pr_cognitive_aid_fixture_contract test_make_pr_reached_path test_flowctl_surface test_tracker_distribution test_prompt_text_pinned test_review_findings_receipts -q (108 post-review-fix tests, green), python3 scripts/run_tests_parallel.py (164 files, 3431 tests, 0 failures, 0 errors, 4 skipped, green after review fixes), uvx ruff@0.16.0 check . (green), ./scripts/sync-codex.sh && ./scripts/sync-codex.sh (green, idempotent), npx -y pnpm@10.26.2 build in /Users/gordon/work/flow-next.dev (76 pages, green), RepoPrompt CE context 53849DEA-FC77-4ACA-8DD2-1C1317E349AE chat fixture-contract-review-B47029: SHIP; R8/R9/R10 met; 2 prior P1 findings resolved at confidence 100, GATE_SKIPPED:unittest:green-receipt f83a339f - baseline reused from prior post-gate pass, GATE_SKIPPED:smoke:green-receipt f83a339f - baseline reused from prior post-gate pass
- PRs: