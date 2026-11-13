---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-323-land-and-merge-evidence-over-bitbucket.1 Implement land and merge evidence over Bitbucket pull requests

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
land and merge evidence over Bitbucket Cloud pull requests.

- flowctl Bitbucket adapter: readiness read (worst build status on the current head, Bitbucket's own merge checks read as a complete listing holding the git mergeability answer, approvals and requested changes, squash allowed, draft) and merge-evidence read (the branch's pull requests and each merged one's old and new paths); malformed or incomplete answers are not-ready or a probe error.
- land forge-bitbucket.md: reads, stops, squash merge with no auto-merge, a re-read right before the merge and a merged-head comparison after it (Bitbucket cannot pin a merge to a head, measured); merged replays read specs from the squash merge commit.
- Fixed resolve-pr's current-branch lookup: beside `q`, Bitbucket ignores `state` (measured), so the state rides in the query.
- Live recordings from flownextnew/flownext with approval states from a second workspace user; test_land_bitbucket.py; live walk of the reference merged pull request 10.

stage: impl-review - ran (codex, gpt-6.1-sol): NEEDS_WORK (6 findings, fixed in 2fa38fd91), then SHIP on the single re-review (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: b3cdc90b6cfcd296274adbb2dc29961f37f1db4a, 8ab625e649ff56a63801dd91fc3bbe09c23a0611, 2fa38fd91de8135a578025df9797858d7193cb02
- Tests: python3 scripts/run_tests_parallel.py (4274 ran, 0 failures); focused unittest test_land_bitbucket test_forge_bitbucket test_forge test_land_gitlab test_tracker_status test_sync_codex_check (OK after fixes); live walk of land forge-bitbucket.md merging flownextnew/flownext PR 10
- PRs: