---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-321-bitbucket-cloud-forge-adapter-and-make.1 Implement Bitbucket Cloud forge adapter and make-pr over Bitbucket pull requests

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Bitbucket Cloud forge adapter and make-pr over Bitbucket pull requests.

- flowctl: `bitbucket` adapter (list_prs) and static hosts bitbucket.org / ssh.bitbucket.org / altssh.bitbucket.org; reads via `bkt --context <Cloud context> api`, paged with a completeness check, fork rows excluded, a branch's rows carry full SHAs (local clone, then commit read) and a merged row's merge time from its activity; every failed or malformed read is a probe failure.
- make-pr: preflight Bitbucket arm (bkt installed and logged in before any close or push), `make-pr-bitbucket.sh` helper for list/view/create/edit in gh's argv and keys, create refuses an open PR on the branch, retry on Bitbucket's exact branch-not-found answer, merged parent with deleted branch resolved from the child's history.
- resolve-pr and land stop NEEDS_HUMAN on Bitbucket (fn-322, fn-323 follow).
- 27 live fixtures from flownextnew/flownext; test_forge_bitbucket.py and test_make_pr_bitbucket.py; live e2e on the test repo opened, refused a duplicate of, and updated PR #8.

stage: impl-review - ran (codex, gpt-6.1-sol high): NEEDS_WORK (4 findings, all fixed in 3276daf0a), then SHIP on the single re-review (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 5d33dd6daf7132bc92ee596bc01259fa27126533, b7e61736c79e59ca5c9154f468236eaa0a29372d, 3276daf0afad2b629698ea11a7dc2ff082d1a855
- Tests: python3 scripts/run_tests_parallel.py (4244 ran, 0 failures); focused unittest test_forge test_forge_bitbucket test_make_pr_gitlab test_make_pr_bitbucket test_codex_config_merge test_flow_auto test_chain_consumer_fixtures test_sync_codex_check (OK after fixes); live e2e on flownextnew/flownext
- PRs: