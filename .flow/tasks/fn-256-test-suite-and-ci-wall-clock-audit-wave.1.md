---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9]
---
# fn-256-test-suite-and-ci-wall-clock-audit-wave.1 Implement Test suite and CI wall-clock (audit wave 2)

## Description
Implements R1-R9 of the parent spec in one pass. The evidence the criteria ask the receipt to carry is recorded below.

### R1 - local suite wall time, same machine

`python3 scripts/run_tests_parallel.py`, jobs=30, 32 cores:

| Run | Before (2f873054) | After |
|---|---|---|
| Paired back-to-back, same load (10:47-10:53, machine loaded) | 213.36s | 126.46s |
| Unpaired (before idle 10:17; after 10:40 under heavier load) | 156.48s | 113.13s |

Pass/skip: before `files=234 ran=5044 failures=0 errors=0 skipped=7`; after `files=236 ran=5046 failures=0 errors=0 skipped=7`. The +2 ran is +6 new tests (support/runner parity, template isolation and copy failure, submission order, sync-codex check) minus the R7 merge (-1) and the R9 deletions (-3). Skip counts match.

Entry-point opt-outs that stay on the real entry: `test_startup_bootstrap.py` and `test_bin_launcher_parity.py` (product entry parity), `test_cmd_usage.py` (exercises `python3 <flowctl.py> usage` on the real script and on copies), and spawns of copied/installed `flowctl.py`, the launchers, or `flowctl_bootstrap.py` (`test_tracker_distribution.py`, `test_managed_review_execution.py`, `test_chain_consumer_fixtures.py`, `test_qa_writer_shell.py` shell block).

### R8 - Windows slowdown diagnosis

Cause: **git cost**. Each Windows `git` process spawn costs roughly 25-70 ms more than on ubuntu, and these three files are dominated by git spawns. flowctl spawn cost is excluded: they spawn flowctl at most twice.

Dispatched run: `workflow_dispatch` run 36230507407 on main (b334b5d7), `suite_mode=serial`, `pattern=test_[pr][re][iv_]*[ltc].py` (the three files plus four neighbours), jobs=1, so there is no parallel contention. Per-file seconds (ubuntu / macos / windows):

| File | ubuntu | macos | windows | win/ubu | git spawns (local census) | flowctl spawns |
|---|---|---|---|---|---|---|
| test_prime_eval.py | 5.9 | 17.5 | 74.6 | 12.7x | 974 | 2 |
| test_review_fanout.py | 7.4 | 20.0 | 39.9 | 5.4x | 1002 | 0 |
| test_pr_cognitive_aid_multi_spec.py | 1.8 | 5.6 | 11.0 | 6.1x | 368 | 0 |

That puts the Windows excess per git spawn at about 71 ms (prime_eval), 32 ms (review_fanout) and 25 ms (multi_spec). The same files in the full parallel main run 35932249551 (jobs=4) took 110.0s, 67.2s and 45.8s on Windows, so contention multiplies the per-spawn cost 1.5-4x. Files dominated by python spawns (memory, chart, spec_chain) are only about 1.3x slower on Windows.

Per-class local census, git spawns per class: prime_eval Topology 165, StacksAndShape 151, SubstanceCiSecretsApi 150, BlobDedup 86, FixtureFamilies 76, PerformanceAccounting 64, Lifecycle 62. The spawns spread across per-test fixture repos (`git -C` builders), so no single named fixture accounts for the cost. review_fanout: 1002 git spawns in TestReviewFanout (init/config/add/commit per test plus in-process rev-parse/diff/merge-base). multi_spec: 367 git spawns in ClosedRangeTests.

Inconclusive part: **per-test Windows timings were not captured.** On Python 3.11 the dispatch inputs cannot emit them: unittest has no `--durations` before 3.12, and the runner prints shard output only for failing files. Adding that output is a runner flag this wave's boundary excludes. Per-test attribution therefore rests on the local per-class census plus the dispatched per-file Windows timings above.

### R9 - converted tests

- `test_interview_source_tags.py`: deleted `test_merged_body_contract_tags_new_criteria_only`, `test_write_back_carries_the_hard_rules` and `test_strategy_long_form_matches_capture_workflow` (sentence pins). `test_skill_md_states_per_pass_user_semantics` became `test_skill_md_routes_to_both_pass_references` (links only). `test_tag_definitions_match_capture` became `test_user_rows_keep_their_decision_tokens` (shared-definition sentences dropped; decision tokens and route kept). `test_write_back_shows_trailing_token_format` lost its phrase pin and kept the format regex.
- `test_work_reached_path_routes.py`: `test_common_work_lifecycle_and_no_forbidden_gate_regrowth` became `test_common_work_lifecycle_routes_and_no_forbidden_gate_regrowth`. It keeps the tokens (`host-deferred`, `Tracker sync:`, the make-pr handoff line), the `references/wave-join.md` route plus that file's existence, and the negative pins. The six sentence pins are gone.
- `test_prompt_text_pinned.py` is untouched.

### Follow-up (not built)

The local critical path is now `test_chain_consumer_fixtures.py` (~110-140s): 183 spawns of a staged `bin/flowctl` launcher, whose bootstrap recompiles flowctl.py from source on every spawn. That is the product entry the spec keeps unchanged.
## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
