---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-291-preserve-successful-claude-reviews-with.1 Preserve successful native Claude review results

## Description
TBD

## Acceptance
Every R-ID in the parent spec Acceptance Criteria is satisfied; judge this task against the spec criteria directly.

## Done summary
Preserve valid Claude success envelopes despite unknown-model stderr diagnostics. Reject malformed or wrong-typed envelopes and nonzero exits without fallback, verdict, receipt or cache; retain genuine zero-exit model-unavailable fallback. Existing driver, finalizers, sessions and other backends remain unchanged. R1-R5 satisfied; both prior P1 findings fixed.

Validation: 82 focused tests passed. The first full offline run executed 4002 tests with 7 skips, 0 assertion failures and 26 errors caused by sandbox restrictions on simulated HTTP listeners. The two affected suites subsequently passed all 134 tests with a narrowly permitted local test listener; source and assertions were unchanged. Ruff 0.16.0, tracker manifest, generated Codex mirror, document anchors and Git checks passed. macOS validation only; Linux/Windows CI and live-provider smokes were not run.

stage: impl-review - SHIP, independent Codex gpt-6-sol/high; snapshot 39308b309fde394f4f18e8ac12f1fb7593844404..57eaa175861a8cd1b51f5eceb515ec765726e890; reservation dc7b695a7b0744aa84eddd07382ea5c3.
stage: completion-review - skipped(policy: single-task, per-task SHIP covers spec surface)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: b9db68b1093de7e05bdca625d4a31908c1368458, 32c14fb147da17ee537a232e90e0686c1271167f, acfd179ae82bda87e659e97ac642823cc4217a74, 57eaa175861a8cd1b51f5eceb515ec765726e890
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p test_claude_review_commands.py, python3 -m unittest discover -s plugins/flow-next/tests -p test_model_resolution.py, python3 scripts/run_tests_parallel.py --jobs 4 (initial exit 1: 26 sandbox HTTP-listener errors; 4002 tests, 7 skips), Isolated offline rerun: test_managed_review_execution.py and test_tracker_executor.py (134 passed), ruff check ., python3 scripts/gen_tracker_manifest.py --check, bash scripts/sync-codex.sh --check, python3 scripts/check_doc_anchors.py, git diff --check
- PRs: