---
satisfies: [R3, R4]
---
# fn-193-deterministic-diagnostics-honest-lock.2 review-attempt rows carry the resolved model/effort (dispatcher-known only)

## Description
R3+R4 in plugins/flow-next/scripts/flowctl.py: add reviewed_model/reviewed_effort Optional[str] kwargs to _record_review_attempt_locked (~:10858 signature; row constructor ~:11214-11266); write row['model']/row['effort'] ONLY when non-None (conditional-key idiom like tool_calls/base_sha ~:11261) - absent, never 'unknown'/'auto'. Source from the SAME values that feed the receipt (_receipt_model_effort ~:4525-4551 - the fallback-ladder downgrade and codex-resume carry must be what lands on the row); thread via _finish_backend_exec (~:42541) alongside reviewed_head_sha/reviewed_base_sha (call sites ~:42375/:42394/:42442/:42471/:42833) and journal + crash-replay them like the fn-183 fields (~:11075-11081, :11953-11955). Surface in review-rounds attempts --json. Do NOT add a --model flag to review-rounds record (~:30614) - host/rp paths must not let a narrating agent claim a model (mirror the measured_tool_calls codex-only posture, flowctl.py ~:4902-4912). R5(e-f) tests: a codex-dispatched attempt row carries model/effort; an rp-recorded row lacks the keys; journal replay preserves them (tests/test_review_convergence_journal.py harness). Docs: plugins/flow-next/docs/architecture.md review-bookkeeping section documents the keys under the existing absence-means-unknown paragraph. FORBIDDEN: journal/receipt schema changes beyond the two additive row keys; publishing anything to the PR; config keys; touching config_lock (task 1).

## Acceptance
R3+R4+R5(e-f) met; test_review_convergence_cap + test_review_convergence_journal green (BARE runs); ruff clean.

## Done summary
Attempt rows gain conditional model/effort keys sourced from the same _receipt_model_effort values as the receipt (ladder downgrades and codex-resume carries land honestly), threaded through _finish_backend_exec on both verdict and transport-failure records, journaled and crash-replayed; attempts --json passes rows unprojected (pinned); record still rejects --model at argparse (pinned). 7 new tests, 314 total green.
## Evidence
- Commits: 3ac52bd5
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_review_convergence_journal -q
- PRs: