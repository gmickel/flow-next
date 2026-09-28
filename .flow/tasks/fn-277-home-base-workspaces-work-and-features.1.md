---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-277-home-base-workspaces-work-and-features.1 Implement home-base sibling repos in work and features status

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Work records sibling repo bases in .flow/tmp/spec_base_repos (cleared per run by the branch fence) and classifies inside each; tier-B only when every repo qualifies. Feature-map update reads sibling diffs. features status --repo adds sibling surface commits since the proof date (UTC cutoff), per-repo counts, loud failure on a non-root/bad path; home repo output unchanged. Callers (maintain, flow, prime, setup) pass --repo. Codex review SHIP after 2 findings fixed (stale sibling file, UTC sibling cutoff) and 1 self-inflicted R4 regression reverted.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 4d7e917f48507e1a5b27d30bf207511da997de7b, 103b649ff130af85942b243e25c5ba8acd0f42df, a0144401b4af3ff75c1ce637ae7c2204892fc68b
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: