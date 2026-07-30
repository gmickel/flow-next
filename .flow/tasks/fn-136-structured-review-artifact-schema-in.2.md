---
satisfies: [R1, R2]
---
# fn-136-structured-review-artifact-schema-in.2 Deterministic finding parser in flowctl

## Description
Implement the pure-stdlib parser and finding-lineage model for the versioned `findings` container.

**Size:** L

**Files:** flowctl.py parser/lineage helpers, dual-copy pin, focused fixtures/tests.

### Approach
- Parse current review fields into canonical P0-P3 severity, confidence anchors 0/25/50/75/100, introduced/pre_existing classification and open/fixed/not_fixed/withdrawn status.
- Generate deterministic round-1 IDs from source receipt identity plus ordinal. Carry IDs through ratchet `Prior finding N` forms; new later findings get new IDs and explicit lineage where needed.
- Parse portable anchors only when path, side/line and base/head context are available. Never guess an anchor; preserve rename/original-path metadata when evidenced.
- Preserve explicit receipt/round/supersedes context and canonical finding order.
- Tolerate observed backend label variants. Unknown enums/unsupported versions retain prose as unsupported; wholly unparseable output emits no structured container and never raises.
- Enforce the contract's 1 MiB parser-input limit, 256 KiB encoded-container limit, 200-item limit and per-field/array limits; cover overflow fallback plus arbitrary-text never-throws behavior.
## Acceptance
- [ ] Parser emits the exact versioned findings schema, canonical enums, stable lineage IDs, portable anchors and ordering (R1).
- [ ] Real backend and ratchet fixtures prove identity carry-forward, no guessed anchors, all numeric bounds, unsupported-version behavior, degrade-to-prose and never-throws safety (R2).
## Done summary
Implemented and hardened the deterministic v1 review-findings parser: canonical enums and ordering, durable ratchet lineage, portable anchors, strict bounds, invalid-vs-absent structured input handling, and fail-closed behavior for unknown prior statuses and malformed/partial host tables. RepoPrompt review converged to SHIP in the required branch-local chat; focused tests, pinned Ruff, Codex mirror idempotency, distribution parity, and the 3,348-test full suite are green.
## Evidence
- Commits: 023cb395a352bbe3eced35d4042ac8c21ddb254a, fdf20e965cf1659291a1768faaafb31288f98728, 9f3b4505d62aa7ec1a784d10f83f691c7bd46871, 3d21db59f26cbb5347e795ac7416059381ebbfdc, 8ed371cc99f3cb42afba1725b173be22f4a86f6b, b7e803869f123a0397735d1f4f94fc55bcc8fd32, ee198a4c820288b88a7c03feb23ba55b3cdf7647, 38523c4816312954f47fba6084e2f35794585f72, 4c46289c9b3e26f9d72ca193097e1d65a6493acb
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_review_findings_parser test_tracker_distribution -q, cd plugins/flow-next/tests && python3 -m unittest test_review_findings_parser test_tracker_package_import test_tracker_distribution -q, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh (twice; idempotent), python3 scripts/run_tests_parallel.py
- PRs: