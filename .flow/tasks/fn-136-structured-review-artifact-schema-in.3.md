---
satisfies: [R1, R4]
---
# fn-136-structured-review-artifact-schema-in.3 Receipt-write integration across backends

## Description
Integrate the versioned findings container across every review receipt writer and enforce currentness without adding I/O.

**Size:** M

**Files:** flowctl receipt-write paths for all backends/review kinds, receipt validation/currentness helpers, focused tests and benchmark.

### Approach
- Attach the parsed container where reviewer output is already in memory. Keep legacy receipts valid and attempt/refund records non-colliding.
- Persist sourceReceiptId, reviewKind/backend, round, base/head SHAs and supersedesReceiptId. Validate IDs, enums, anchors, references and duplicate lineage.
- Define current state solely from the newest explicit supersedes chain member whose head matches the current review head. Stale receipts stay visible evidence but never current resolution state.
- Benchmark the largest pinned finding fixture. Parsing/validation must add no model/network I/O and remain under the documented local budget.
## Acceptance
- [ ] Every backend/review receipt writer emits the optional versioned container; legacy receipts remain valid (R1).
- [ ] Supersedes/head rules deterministically select current finding status while preserving stale evidence (R4).
- [ ] Pinned benchmark passes and inspection proves no added model/network I/O (R4).
## Done summary
Integrated structured findings across review receipt writers with immutable generation history, deterministic currentness projection, durable lineage ownership, and fail-closed fallback for unparseable re-reviews. Added backend, concurrency, recovery, QA, lineage, currentness, import-safety, CLI-surface, clean-tree, and local-budget regressions; RepoPrompt same-chat review returned SHIP.
## Evidence
- Commits: 2bad9dbb13e02e148aac5a66c0ab6ac978f513a9, 1315b4f0622bba505833b218f62e20fb192cc477, 9e547d7d8f52b46662157ba35eee141dae3e6499, 09a80e9dcac9bb9ec27432c1c783b1c9b59d3c0f, 44846cf32bf6131d3230c6e0ccdf1e11f7a75b58, d34f0f97b477f8c2a46569a8e2dbfdc5d5037205, 41188b986677d0aa69c5790a1ce0ff87eb0e2eeb, fb2657066042ffb7f281cea69d156f03a1d37d4b, c1acdf7f1e39441aed0abff832e92789169b7ad1, 332610b49fa0071b9c0b78c425d757f129d2767b, 2fd04fbd4c0549e7cf267a6dfba4875318f740d2, a5084fffb9cb4b8f4024b64e7075c7fafc2f8127
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_review_findings_receipts test_review_findings_parser test_tracker_package_import test_flowctl_surface -q (76 passed), python3 scripts/run_tests_parallel.py (3377 passed, 4 skipped), uvx ruff@0.16.0 check . (passed), ./scripts/sync-codex.sh twice (idempotent), RepoPrompt CE same-chat review context 675A514E-CF17-44C4-BD18-CFFE0BD96FD0 chat receipt-findings-review-A8D946: SHIP; receipt /tmp/impl-review-receipt-fn-136-structured-review-artifact-schema-in.3.json
- PRs: