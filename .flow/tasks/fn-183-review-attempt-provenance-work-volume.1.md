---
satisfies: [R1, R2, R3]
---
# fn-183-review-attempt-provenance-work-volume.1 Attempt-row write path: output bytes, tool-call count, base_sha, head_sha_observed

## Description
Spec fn-183 items 1-3 (#312). record_review_attempt gains output byte count (always), tool-call count (where the backend reports it; absent otherwise, never fabricated), base_sha forwarded from _capture_review_snapshot on paths where it runs (absent, not guessed, elsewhere), and head_sha provenance (marker or omission - pick one, document it). The rp/host review-rounds record CLI path is the fallback fixture. Ledger schema rides the existing hash_epoch discipline.

**Files:** plugins/flow-next/scripts/flowctl.py (`record_review_attempt`) + `.flow/bin/flowctl.py` dual copy; attempt-row tests

## Acceptance
R1, R2, R3 of the spec.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
