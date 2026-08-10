---
satisfies: [R6]
---
# fn-180-declared-vs-evidenced-r-id-coverage.4 Docs, CHANGELOG, propagation + full gate

## Description
Spec fn-180 R6. flowctl.md validate section + make-pr skill reference updated; CHANGELOG Unreleased crediting @sn-furali (#301, #302). Dual copies, manifest, sync-codex twice, full suite + ruff.

## Acceptance
R6 of the spec. Full gate green; no version bump.

## Done summary
R6 closed out. flowctl.md validate section documents the orphaned-evidence warning (three-state contract, foreign tokens ignored by design, read-only, constant two-spawn cost safe for the land loop); export-cognitive-aid section documents undeclared_r_ids beside uncovered_r_ids (plan-gate vs merge-gate questions, residue qualifying both denominators). CHANGELOG Unreleased entries, user-outcome-first, credit @sn-furali for #301 and #302. Full gate green; no version bump.
## Evidence
- Commits: b8449b99
- Tests: python3 scripts/run_tests_parallel.py (4406 OK), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent)
- PRs: