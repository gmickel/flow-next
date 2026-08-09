---
satisfies: [R6]
---
# fn-181-state-provenance-status-source-review.4 Docs, CHANGELOG, propagation + full gate

## Description
Spec fn-181 R6. flowctl.md documents status_source and the advisory; CHANGELOG Unreleased crediting @sn-furali (#304, #307 with the rescope noted). Dual copies, sync-codex twice, full suite + ruff.

## Acceptance
R6 of the spec. Full gate green; no version bump.

## Done summary
flowctl.md documents status_source (show/list), the absent-runtime advisory, and the ready/anchor behind-upstream advisory with the explicit list/status/next exclusion. CHANGELOG Unreleased entry (user-outcome-first) credits @sn-furali for #304/#307. Full gate green: run_tests_parallel 4313/0/0, ruff clean, sync-codex idempotent, dual copies + manifest current.
## Evidence
- Commits: 784b1558
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: