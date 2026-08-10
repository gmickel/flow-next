---
satisfies: [R5]
---
# fn-183-review-attempt-provenance-work-volume.3 Architecture notes, docs, CHANGELOG + full gate

## Description
Spec fn-183 R5. Architecture notes: what each field answers; absence means unknown; session_id explicitly documented as NOT a work-evidence signal (resume path reuses it). CHANGELOG Unreleased crediting @sn-furali (#312). Dual copies, sync-codex twice, full suite + ruff.

## Acceptance
R5 of the spec. Full gate green; no version bump.

## Done summary
R5 closed out. architecture.md "Review bookkeeping" section documents each new attempt-row field and what it answers (output_bytes = did the verdict cost measured work; tool_calls = measured-only, recorded 0 is the fabrication signal; head_sha_observed = snapshot vs finalize-time fallback, marker not omission so fallback rows stay distinguishable from pre-fn-183 rows; base_sha = locate and re-render the judged diff), states absence means unknown never zero, and documents session_id as NOT a work-evidence signal (resume reuses the thread id). flowctl.md attempts surface links to the schema notes. CHANGELOG Unreleased entry, user-outcome-first, credits @sn-furali (#312). Full gate green; no version bump (batched release).
## Evidence
- Commits: 17fe7a7b
- Tests: python3 scripts/run_tests_parallel.py (4340 OK, 0 failures), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent, no diff)
- PRs: