---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-311-baseline-close-and-duplicate-scan-gaps.1 Implement Baseline, close and duplicate-scan gaps

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
The worker's pre-edit baseline records a Quick command whose target the spec has not created yet as `baseline: pending (<cmd>)` and judges the rest on its own result; an exit code the spec names as a normal result counts as green in the baseline and every gate. The rolling scheduler's first-batch baseline points at the same rule (#552, R1, R2).

`flowctl show --json` gains `completion_review_pending`, computed with the tracker status policy's own `_completion_review_configured` and `completion_review_satisfied`. make-pr's preflight leaves such a spec open: attended it opens a draft with a note naming the status and the close steps; autonomous it exits 2 before any close, commit or push. `not_required` still satisfies (#477, R3, R4). Tests: three unsatisfied statuses keep the spec open; ship, not_required and no review close as before; the field agrees with the tracker fold across all three precedence levels and the off values. The new tests fail against main's scripts.

Capture's duplicate scan also compares against spec ids at the tips of local and remote-tracking branches that the working tree lacks, with no fetch (#444, R5). Shown on a throwaway repo: session B listed `fn-2-widget-cache-stale-entries` committed on session A's unmerged worktree branch. A history-based listing was rejected because it surfaced specs deleted from main.

CHANGELOG credits added (R7). No stage, config key, command or question added (R6).

stage: impl-review - ran (model: codex gpt-6.1-sol high; round 1 three reviewers, contracts NEEDS_WORK; message fixed, missing-tracker-package finding declined; re-review SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 6f8ee486c57c3c740da69f2f1867a1470174e4fd, e482810eb07dd299e58c344516b24d003a967a21
- Tests: python3 -m unittest test_make_pr_close test_make_pr_preflight_auth test_make_pr_reached_path test_bundled_make_pr test_tracker_conformance
- PRs: