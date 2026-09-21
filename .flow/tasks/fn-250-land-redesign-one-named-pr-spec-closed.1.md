---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11]
---
# fn-250-land-redesign-one-named-pr-spec-closed.1 Implement Land redesign: one named PR, spec closed at the PR head

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Closing a spec now commits each task's final status, make-pr closes the spec as the last commit before it opens the pull request, and creating or starting a task reopens a closed spec (R1-R3). Land is rewritten as short prose over one named, currently authorized pull request, flow's landing stage passes it that pull request and the authorization, and the docs carry the repo-wide recipe, the review-gate options, the chain-child rebase and the upgrade notes (R4-R11).

Land skill instruction text, references included: 1,741 lines before, 185 after (R9 bound: under 200). The rewrite commit deletes 1,721 lines from the land skill and adds 165. Eight `land.*` keys are retired (`release`, `reviewSignal`, `automatedReviewers`, `reviewTrigger`, `ciFixBudget`, `cleanReviewCommentPattern`, `requestReviewers`, `patienceMinutesAfterReview`); `land.mergeVerdictCommand` and `land.patienceMinutes` remain; the `land` schema object is open so a legacy key still loads. The unused `clean-review` judge preset is removed from flowctl.

Tests per R-ID: `test_spec_close_reopen.py` (R1, R3 and their error cases), `test_make_pr_close.py` (R2: incomplete task, dry run, failed close, failed commit), `test_land_named_pr.py` and `test_land_tracker_api.py` (R4-R8 error cases), `test_land_config.py` (R9 legacy-key load), `test_flow_merge_destination.py` and `test_judge_route.py` (R10), `test_land_upgrade_docs.py` (R11). Retired with the machinery they pinned: `test_land_chain_fixtures.py`, `test_land_merge_cmd_shell.py`, `test_land_patience_after_review.py`, plus the land sections of `test_land_config.py`, `test_judge_consumers.py`, `test_tracker_caller_execution.py` and `test_skill_prose_diet.py`. The full suite runs 4,921 tests against a 5,042 baseline for that reason.

Worker corrections to the child's range:
- Unit 2: the child removed make-pr's existing Ralph/autonomous refusal to open a PR for an incomplete spec (exit 2) and deleted its two pins. R2 does not ask for that, so the guard and the pins in `test_make_pr_reached_path.py` and `test_skill_prose_diet.py` are restored, and the new R2 test asserts the refusal. Reviewer: confirm this reading of R2's "opens the pull request without closing and says so".
- Units 1-2: both new test files failed the package-import gate (`test_tracker_package_import.py`) because its textual matcher wants `scripts` on the `sys.path.insert` line. The tests now use the canonical form; the gate is unchanged.

For the reviewer:
- make-pr now refuses a dirty tree before the close commit. That is a new stop the spec does not name; it keeps the close commit limited to the spec and task files.
- `judge_route_lifecycle` sends a closed spec with no observed PR to the host instead of make-pr, from R10's "never replaced" clause. A make-pr run that closed and then failed to open the PR lands on that route.
- One released CHANGELOG entry had a link to a deleted land reference file; the link is repointed and nothing else in released sections changed.
- No version bump, tag or release section; notes sit under `## Unreleased`. flow-next.dev is untouched.

The sandbox (`workspace-write`, linked worktree) denied `git commit` in all five runs, as expected; the worker committed each child tree with `git add -A`. Unit 3 ran past the host's 600 s tool limit, was moved to the background, and was blocked on until its exit code (0) was read.

Tier: implementer = gpt-6-astra at medium (explicit invocation; reached over the codex CLI bridge)

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: implement - ran (model: gpt-6-astra at medium via codex exec, 5 runs, one per scope unit; delegated: 8)
## Evidence
- Commits: 442bd99a6b5386e7d33239aeceaac5faffd4a6cf, 971981fe964cedd9ef595ceb00c1849fbf6fba03, 9de2518f6b12eecd34a008f9e91eb0c0deb8078a, 22d399189360bc587f8f5a661c5b4a4c2da4225e, 0ad93cdd452293219c0c1e6a73563d80ffe4f73b, 4983e4152076db128495df595dc44b94cbcd6ad0, 5b51b490e5e287297a328885d133cfe986089c67, 99a0e4dae789a8ba55366dc5cca13b444962f79d, 3f83ca1257d9fecaea17466c8191d969a94efe1e, 46446671187a098067cb14a04b5b1934bfabaf3a, a83f1cd6412f512cf033d982622e5893e3c00154, 3296f62e98b15a5f06c66f50312b675008e4aff3
- Tests: baseline: green (python3 scripts/run_tests_parallel.py rc=0, files=225 ran=5042; uvx ruff@0.16.0 check . rc=0), python3 scripts/run_tests_parallel.py (final tree 5b51b490: rc=0, files=227 ran=4921 failures=0 errors=0 skipped=7; green receipt .flow/tmp/green-receipts/5b51b490-unittest.json), uvx ruff@0.16.0 check . (final tree: rc=0), ./scripts/sync-codex.sh x2 (second run no-op), python3 scripts/gen_flow_config_schema.py --check (rc=0), python3 scripts/run_tests_parallel.py on the tree merged with the integration branch (4939 ran, 0 failures, exit 0), uvx ruff@0.16.0 check . (exit 0), python3 scripts/gen_flow_config_schema.py --check (exit 0), python3 scripts/check_doc_anchors.py (exit 0)
- PRs: