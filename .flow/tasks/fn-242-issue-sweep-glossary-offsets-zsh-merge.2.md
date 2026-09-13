---
satisfies: [R5, R6, R7]
---
# fn-242-issue-sweep-glossary-offsets-zsh-merge.2 Merge-evidence file scope (#391) and ci-fix checkout hint (#411)

## Description
TBD

## Acceptance
R5, R6 and R7 in the parent spec's ## Acceptance Criteria are satisfied; judge this task against the spec's criteria directly.

## Done summary
R5 (#391): `merge_evidence` now probes each MERGED row's changed files through the executor (`merge-evidence-files`, `gh pr view <n> --json files`, idempotent GET) and ignores rows whose whole diff is `.flow/specs/` or `.flow/tasks/` (a spec-only-merged branch classifies `none`); a probe failure or a number-less merged row yields `probe-error`, never `merged`. `_classify_pr_rows` stays pure and takes the precomputed spec-only number set. R6 (#411): one sentence in land's ci-fix step 1 (canonical + Codex mirror) tells the agent to run the fix in the path git names on `already checked out at`, skipping the checkout and that checkout's branch restore, never creating or removing a worktree. R7: two Fixed entries under Unreleased crediting @sn-furali (#391) and @TechupBusiness (#411); no version bump.

Tests: `MergeEvidence.test_spec_text_only_merge_is_not_evidence` (spec-only, spec-only + open, mixed, two merged one spec-only, transport error, non-JSON body, missing number) and `test_open_and_closed_rows_are_never_file_probed`; merged fixtures now carry a PR number (`MERGED_ROWS`) and the fake executor defaults the files probe to shipped code; two op-sequence assertions gained the new probe. MANIFEST.json regenerated.

Follow-up (not built): `docs/tracker-sync.md` and `status-sync.md` describe the merge-evidence gate by PR state only; a one-line mention of the file-scope rule is a docs task outside this task's allowed edit list.

stage: impl-review - ran (codex:gpt-6-astra:medium, single correctness draw, SHIP first round, receipt /tmp/impl-review-receipt-abf191ec0723-fn-242-issue-sweep-glossary-offsets-zsh-merge.2.json)
## Evidence
- Commits: 1134ea1f0659a567066523448990d1716e09cd88
- Tests: baseline: green via handoff (verified at 2eab4587 by fn-242-issue-sweep-glossary-offsets-zsh-merge.1), python3 scripts/run_tests_parallel.py (files=217 ran=4910 failures=0 errors=0 skipped=6; green receipt 1134ea1f-unittest), uvx ruff@0.16.0 check ., bash scripts/sync-codex.sh (run twice; second run left the tree unchanged), python3 scripts/gen_tracker_manifest.py --check, cd plugins/flow-next && python3 -m unittest tests.test_tracker_status -k spec_text_only (red against pre-fix policy.py: 5 subtests 'merged' != expected; green after fix)
- PRs: