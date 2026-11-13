---
satisfies: [R1, R2, R3, R4]
---
# fn-322-resolve-pr-over-bitbucket-pull-request.1 Implement resolve-pr over Bitbucket pull request comments

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
resolve-pr over Bitbucket Cloud pull request comments.

- Scripts beside the GitLab ones, sharing `bb-target` (Cloud bkt context, origin repository, paged reads that fail unless complete): `get-bb-comments` (get-pr-comments keys; every unresolved top-level comment, inline or general, as a review thread with its replies grouped under it; deleted skipped; outdated when Bitbucket kept the comment on an earlier head), `get-bb-current-pr`, `get-bb-pr`, `reply-to-bb-comment`, `resolve-bb-comment` (409 already-resolved counts as settled).
- resolve-pr `forge-bitbucket.md` gives each phase's command; land's stub stays until fn-323.
- 12 live recordings from PR 9 of flownextnew/flownext; test_resolve_pr_bitbucket.py; live walk of the reference's steps on PR 9 fixed, pushed, replied to and resolved a new comment.

stage: impl-review - ran (codex, gpt-6.1-sol): NEEDS_WORK (2 findings, fixed in c63947f8f), then SHIP on the single re-review (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 151c1eee8147a9ab0e0a5fbd419fc72a8906c177, 7d54a3abe4284cdacb364d9e8104277bd2e30a82, c63947f8fb7394d34162554efbfbdbb0cb523bc1
- Tests: python3 scripts/run_tests_parallel.py (4260 ran, 0 failures); focused unittest test_resolve_pr_bitbucket test_resolve_pr_gitlab test_make_pr_bitbucket test_forge_bitbucket test_sync_codex_check test_codex_config_merge (OK after fixes); live walk of forge-bitbucket.md on flownextnew/flownext PR 9
- PRs: