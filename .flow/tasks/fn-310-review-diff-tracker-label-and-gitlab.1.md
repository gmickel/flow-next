---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9]
---
# fn-310-review-diff-tracker-label-and-gitlab.1 Implement Review diff, tracker label and GitLab probe fixes

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Copilot and Cursor primary reviews now get the reviewed diff by path through one backend-neutral helper (`_attach_review_diff`), as Claude did; deep and validate passes reuse the primary's file (#529, R1).

R2 check, run live on Linux (cursor-agent 2026.10.22): ask mode under `-p --trust` ran `git hash-object` and returned the exact hash, and read a gitignored `.flow/tmp/claude-review/*.diff` with file tools alone. Cursor's support forum says ask mode blocks shell, `git diff` included, where no OS sandbox exists (Windows), so Cursor also gets the diff by path, with a note saying shell "may be blocked".

The GitHub wire label verb cuts names to GitHub's 50-character cap (#578, R3, adapted from PR #581). A remote gh does not know as a GitHub host is "no PR forge" for `judge --preset route` and `pilot snapshot` (#583, R4). make-pr checks origin's own host (SSH aliases via `ssh -G`, GHE via `gh auth token --hostname`) before the gh install and auth checks, and stops NEEDS_HUMAN naming only the host (R5). Claude success envelopes win over the `unrecognized_model` stderr diagnostic, and the model cache records only successful fallbacks (R8, R9, adapted from PR #546). CHANGELOG credits added (R7). Each fix's regression fails on main and passes here (R6).

stage: impl-review - ran (model: codex gpt-6.1-sol high; round 1 three-reviewer panel NEEDS_WORK, R5 guard and R2 Cursor fixed; re-review SHIP)

Follow-up (reviewer FYI, not fixed): with `GH_ENTERPRISE_TOKEN` set, `gh auth token --hostname <any host>` succeeds, so a GitLab origin passes make-pr's forge guard.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: cad626125f02cc0914ada8c9dbfbdff3b7c91b3d, ee361c14ae352297292875af1adf720423a3a401, 23eca0d3f4455ff9e719bfe966f59e43d7cd1395, 0f8efdae11fd6fed5fdfd9e824adf6fb1415afcf, 1fcf738754ef54496f9646c8ed945be9723e0fcd
- Tests: python3 -m unittest test_model_resolution test_claude_review_commands test_managed_review_execution test_review_fanout test_tracker_conformance test_judge_route test_pilot_snapshot test_make_pr_preflight_auth test_make_pr_close test_make_pr_reached_path test_bundled_make_pr test_judge test_judge_consumers
- PRs: