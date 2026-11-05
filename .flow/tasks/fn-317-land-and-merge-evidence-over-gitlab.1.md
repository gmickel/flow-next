---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-317-land-and-merge-evidence-over-gitlab.1 Implement land and merge evidence over GitLab merge requests

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
land merges GitLab merge requests and a merged one is merge evidence. flowctl's GitLab adapter gains a readiness read (head pipeline for the current head, GitLab's detailed merge status with approval approved/required/unknown, the project's squash rule; anything unreadable is not ready) that `pilot snapshot` carries on the selected spec's open MR, and a merge-evidence read (the branch's MRs plus each merged one's changed paths) that flowctl hands to the tracker through a hook; unset, the tracker keeps its gh read. land's new forge-gitlab.md reads specs at `refs/merge-requests/<iid>/head`, gates on readiness from a snapshot run in the head worktree, fixes a failed pipeline once from the failed job logs, finds stacked children with an encoded field, and squash-merges through the merge API pinned to the head SHA; steps with no GitLab arm stop NEEDS_HUMAN. flow's tail binds and observes the MR through the snapshot instead of stopping after make-pr.

Fixtures recorded live on GitLab EE 19.5.3 under the Ultimate trial (approval rule needing a second user, before and after approval; failed, manual, running, skipped pipelines; squash forbidden; moved-head 409; squash merge; spec-only merge); Free-tier MR reads from before the trial cover readiness on Free. 7 deliberate breakages each fail their test.

stage: impl-review - ran [codex 3-lens panel NEEDS_WORK (4 findings, all fixed) -> fix pass a0373f396 -> re-review SHIP] (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: f5c947edc9979fabe2fd14b1739bb1f59966b892, a0373f39674a8bfa5e51c5d2c825338ebe21f778
- Tests: python3 scripts/run_tests_parallel.py (4192 passed, before the fix pass); python3 -m unittest test_forge test_land_gitlab (24 passed, after)
- PRs: