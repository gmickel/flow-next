---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-312-make-pr-update-closes-a-spec-whose-work.1 Implement make-pr --update closes a spec whose work finished

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
`make-pr --update` now runs the same close fence as a create when every task is done and no completion review is pending, so a draft opened with open work becomes landable: the delivery script already pushes on update, so the close commit reaches the PR branch and the body refreshes from the closed head (R1). Updates with open tasks or a pending review, dry runs and already-closed specs change nothing about the close (R2). Both draft notes name `/flow-next:make-pr <spec-id> --update` (R3). Docs (flowctl.md, teams.md, make-pr SKILL.md and workflow.md, the make-pr conduct row) drop "body-only updates never close". CHANGELOG entry added (R5).

R4 test runs preflight and the shipped delivery script against a local bare remote: draft with an open task, an update that still does not close, an update after the task is done whose pushed head carries the close commit and the closed spec, and a second update that commits nothing. It fails against main's scripts and against a mutant with the push removed.

stage: impl-review - ran (model: codex gpt-6.1-sol high; round 1 three reviewers NEEDS_WORK on test depth and a prose-pinned assertion, both fixed; re-review SHIP)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 803a38e8da2d3d91905a120b04b9919bb5b5548e, 0e6e222f93d01504e1c45b5cd4691b90a9508a5c
- Tests: python3 -m unittest test_make_pr_close test_make_pr_preflight_auth test_bundled_make_pr test_make_pr_reached_path
- PRs: