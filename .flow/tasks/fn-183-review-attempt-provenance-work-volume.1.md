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
Attempt-row write path extended per fn-183 R1-R3 (#312). Every new review_attempts row records output_bytes (computed in _record_review_attempt_locked from the output arg; output text never retained). tool_calls recorded only where measured: new count_codex_tool_calls() parses the codex exec --json event stream (None - never 0 - for plain text; unknown future item types count as work), wired at both _finish_backend_exec record sites. head_sha provenance is a marker, head_sha_observed: true|false (marker chosen over omission so fallback rows stay distinguishable from pre-fn-183 rows); the review-rounds record CLI path is the tested fallback fixture. base_sha forwarded via reviewed_base_sha from the existing _capture_review_snapshot unpacks in impl/plan/completion handlers; absent, not guessed, elsewhere. Dual copy + tracker manifests + sync-codex x2 propagated. 12 new focused tests.
## Evidence
- Commits: 07cb1f72
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_review_convergence_journal test_host_review_backend test_flowctl_surface -q (314 OK), cd plugins/flow-next/tests && python3 -m unittest test_tracker_distribution -q (19 OK)
- PRs: