---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-308-wasted-calls-on-the-hot-paths-audit.1 Implement Wasted calls on the hot paths (audit 2026-10 wave 2)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Removed tool, API and re-read calls whose value the run already holds; outcomes unchanged.

- R1: deps runs `flowctl show` only for open specs. On this repo 295 calls became 22; the ready/blocked and phase output is byte-identical (bash and zsh).
- R2: removed five unused repo-root lookups (plan-review, completion review twice, impl-review other-paths, sync), completion review's per-backend spec read (Steps renumbered; the fix loop's re-run points at step 1), and impl-review CLI's recomputed diff base and unused log.
- R3: optional phases dispatch deep-pass and validate through one `codex|copilot|cursor|claude` arm. A stub-flowctl test shows the same invocations as the four old arms; host and unknown backends make no call. V.3 now names every CLI backend, since all four validate commands merge the same way.
- R4: capture's glossary scan and strategy alignment, and refine's doc-aware glossary scan, read the preflight snapshot. A failed, missing or malformed probe falls back to the live call. The snapshot values match the live outputs on this repo.
- R5, R8: withdrawn in the spec.
- R6: resolve-pr's detached push makes one `gh pr view` call and stops before pushing when it fails (test drives a real push to a local bare remote).
- R7: workflow-scout drops `gh run list` and the PR body read. Old and new scout prompts gave the same WP1-WP6 statuses (5/6) on this repo; gh commands went from 6 to 1.

stage: impl-review - ran (model: gpt-6.1-sol) — round 1 NEEDS_WORK (3 findings: malformed-probe fallback, completion re-run step, push exit status), fixed in b5305f06, round 2 SHIP

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: b7d2baf8ce06c9dae5abb8a8e1e4aae2fa7d3647, b5305f0688054225bf0d62aabf7d0ad2b58e2362
- Tests: python3 scripts/run_tests_parallel.py (4081 OK at b7d2baf8); focused: test_snapshot_probe_reads test_resolve_pr_detached_push test_impl_review_optional_dispatch + 7 affected suites (73 OK at b5305f06); uvx ruff@0.16.0 check .
- PRs: