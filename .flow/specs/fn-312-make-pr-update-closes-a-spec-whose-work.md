# make-pr --update closes a spec whose work finished

## Goal & Context

Attended make-pr opens a draft PR and leaves the spec open when tasks are unfinished, or, since fn-311, when a configured completion review has not passed. #459 decided those drafts cannot land, and land stops `BLOCKED: work not finished` while the spec is open. Nothing closes the spec once the work is done. Rerunning make-pr refuses the existing PR, and `--update` never closes. fn-311 works around this with a draft note that tells the person to run `flowctl spec close`, commit, push and mark the PR ready by hand. This spec makes the documented recovery one command: `/flow-next:make-pr <spec-id> --update`. [paraphrase]

<!-- Source: 10% user / 30% [paraphrase] / 60% [inferred] -->

## Architecture & Data Models

The close already exists in make-pr's preflight as one fence: check the close paths are clean, bind `branch_name`, `spec close`, stage the reported paths, commit with the project's message rules. Today the fence runs only on a create. The update path reuses the same fence when the spec's work is complete, then pushes the close commit and refreshes the body, so the body describes the closed head. [inferred]

## Edge Cases & Constraints

- The close happens only when every task is done and `completion_review_pending` is false, the same test a create applies. [inferred]
- An update on a spec that is already closed, a dry run, or an update while work is still open changes nothing about the close, as today. [inferred]
- The PR's draft state is left alone. Marking it ready stays with the person. [inferred]
- The PR head moves by one commit, so land's head-bound gates see the new head as for any pushed fix. [inferred]

## Acceptance Criteria

- **R1:** `make-pr <spec-id> --update` on an open PR whose spec has every task done and no pending completion review closes the spec on the PR branch, commits the close under the same message rules as a create, pushes it, and refreshes the body from the closed head. Errors: dirty close paths, a failed close or a failed commit stop before the push with the same messages a create uses; a failed push stops and reports the push error, leaving the local close commit in place. [inferred]
- **R2:** An update on an already-closed spec, a `--dry-run`, or an update whose spec still has open tasks or a pending completion review changes nothing about closing and keeps today's behaviour. No error surface beyond R1. [inferred]
- **R3:** Both draft notes (open tasks and pending completion review) name `/flow-next:make-pr <spec-id> --update` as the step after the work or review is finished, in place of fn-311's manual close, commit and push. No error surface. [inferred]
- **R4:** A test opens a draft with an open task, marks the task done, runs the update, and shows that the pushed head carries the closed spec and the close commit, and that a second update makes no new commit. [inferred]
- **R5:** A CHANGELOG `## Unreleased` entry describes the new recovery. [inferred]

## Boundaries

- No change to the create path, to land, or to the rule that a draft with an open spec cannot land. [inferred]
- No new flag or config key. [inferred]
- The update does not mark the PR ready. [inferred]

## Decision Context

#459 recorded "dry-run and body-only updates never close" to keep an update free of side effects. This spec keeps that for every update where the spec's work is still open, and narrows it for the one case it left unhandled: the work finished after the draft opened. The alternative, a separate close command, would add a verb for a step make-pr already owns. fn-311's manual instructions stay correct until this lands. [inferred]
