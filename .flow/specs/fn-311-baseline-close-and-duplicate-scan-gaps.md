# Baseline, close and duplicate-scan gaps

## Goal & Context

The 9.5.1 patch release closes valid GitHub issues that sat open too long, without adding machinery, wall-clock or tokens. This spec takes the three gaps in the skills' own rules. Each one either stops an unattended run that should continue, or lets through work that should stop. [paraphrase]

- **#552:** work's first-batch baseline and the worker's pre-edit baseline run the spec's Quick commands at the spec base. A Quick command often names the tool the spec builds, so at the base it fails because the file does not exist yet. The red baseline parks the whole spec before task 1 starts (seen in an unattended `flow --auto --tick`, with the other 167 tests green). A tool with documented non-zero exit codes for normal results trips the same rule after task 1.
- **#477:** make-pr's spec-close fence closes a spec when all its tasks are done. It never looks at the completion review. A spec whose review is configured but `unknown` or `needs_work` closes cleanly, land then merges it, and only the tracker merge-evidence gate notices, after the merge. If the close were withheld, land would already refuse: it stops `BLOCKED` with `work not finished` while a spec is open.
- **#444:** capture's duplicate scan compares against open specs in the working tree only. A spec captured minutes earlier on another session's unmerged branch is invisible to it, so two concurrent sessions mint the same spec. The reporter measured this: two sessions captured one defect hours apart, and four specs existed only on unmerged branches.

<!-- Source: 15% user / 25% [paraphrase] / 60% [inferred] -->

## Architecture & Data Models

- **Baseline.** The rule lives in prose that the worker and the rolling scheduler read. The fix is a sentence of judgment there, telling the agent what does not count as red, plus where to record it. No new spec field, no Quick-command syntax. [inferred]
- **Close fence.** The tracker status policy already decides "completion review configured" (spec `default_review`, then `FLOW_REVIEW_BACKEND`, then config `review.backend`), and `COMPLETION_REVIEW_SATISFYING` (`ship`, `not_required`) decides "satisfied". make-pr consumes that one decision from flowctl. It never re-derives the precedence in bash, so the close and the tracker cannot disagree. [inferred]
- **Duplicate scan.** Capture's candidate set grows to include spec ids present on other local branches and remote-tracking refs but absent from the working tree. Spec ids carry their title slug, so the existing keyword comparison works on them unchanged. One read-only git listing, no fetch. Both listing shapes tried on this repo (2,873 commits, 111 refs) ran in under 0.4 s. [inferred]

## API Contracts

- `flowctl show <spec> --json` gains one additive, read-only boolean that is true when the completion review is configured for the spec and its status is outside the satisfying set. Nothing writes it. [inferred]
- `flowctl spec close` is unchanged. [inferred]

## Edge Cases & Constraints

- `not_required` stays satisfying. A single-task or direct-route spec that work marked `not_required` closes as today, so the default no-plan path is unaffected. Refusing it would undo #371. [inferred]
- Under `FLOW_AUTONOMOUS=1` / `mode:autonomous`, the unsatisfied-review case ends the same way open tasks do today: exit 2, so `flow --auto` stops `NEEDS_HUMAN` instead of opening a PR that land would refuse. [inferred]
- A Quick command that is red for any reason other than "its target does not exist yet" or "a documented normal exit code" stays a red baseline under the existing rule. The agent's call is recorded, so a reviewer can see what was skipped and why. [inferred]
- A git error, a shallow clone or a missing ref in the duplicate scan leaves the scan at its working-tree set and stops nothing. [inferred]
- With the tracker bridge on and tracker-first ids, the scan runs before `tracker create-first`, so a duplicate found on another branch stops before any remote issue exists. [inferred]

## Acceptance Criteria

- **R1:** When a spec's Quick command fails at the spec base only because the file or tool it runs does not exist yet, both the work first-batch baseline and the worker pre-edit baseline record that command as not yet runnable and treat the rest of the baseline on its own result. Task 1 then starts. The command runs in the gate of the task that creates its target, and in every later task. Errors: a Quick command that fails for any other reason is still a red baseline under the existing rule. [inferred]
- **R2:** When the spec's text states that a Quick command's non-zero exit code is a normal result, the baseline and the task gates count that code as green. No error surface beyond the existing red-baseline rule for any code the spec does not name. [inferred]
- **R3:** make-pr does not close a spec whose completion review is configured and unsatisfied (`unknown`, `needs_work` or `needs_human`). Attended, it opens a draft PR with the spec left open and a note naming the review status. Autonomous, it exits 2 with that status in the message, before any close, commit or push. Errors: a configured review with status `ship` or `not_required`, or a spec with no review configured, closes exactly as today. [inferred]
- **R4:** make-pr's decision in R3 comes from the flowctl field in API Contracts, which uses the same configured-review precedence as the tracker status policy. A test sets the backend once through each precedence level and shows that the field and the tracker fold agree. No error surface beyond R3. [inferred]
- **R5:** capture's duplicate scan includes spec ids present on other local branches and remote-tracking refs but absent from the working tree, and scores them with the existing keyword rule. A spec committed on another worktree's unmerged branch is reported as a match. Errors: when the git listing fails, the scan falls back to the working-tree set without a warning loop or a stop. [inferred]
- **R6:** None of R1-R5 adds a stage, a config key, a flowctl command or a question to a run that does not hit the case. [paraphrase]
- **R7:** The CHANGELOG `## Unreleased` entries credit TechupBusiness for reporting #552 and sn-furali for reporting #477 and #444. [inferred]

## Boundaries

- No pre-close hook, refusal seam or credential check on `spec close` (#463, closed). [inferred]
- No completion-review refusal inside `flowctl spec close` itself. The shipped closer is make-pr's fence. A person who runs `spec close` by hand is choosing to close. [inferred]
- No tracker query in the duplicate scan, and no configurable candidate hook. [inferred]
- No Quick-command syntax for expected exit codes. The spec's own prose states them, and the agent reads it. [inferred]
- No new machinery, and nothing that slows a run or adds tokens. [paraphrase]

## Decision Context

#477 asks for two clauses: a refusal in `spec close` and a change to make-pr's fence. Only the fence is needed for the failure that was measured, an unreviewed spec merging through land, because land already refuses an open spec. A refusal inside `spec close` would also need make-pr to stop propagating the refusal as "PR not opened", and that trades a recoverable stale row for a PR that never opens. One read-only flowctl field keeps the "configured" test in one place. [inferred]

#552's reporter offered either a skip rule or new Quick-command markers. Agent first: the agent can see that the target does not exist at the base and that the spec names an exit code. A sentence of guidance and a recorded judgment cover both cases without new structure. [inferred]

#444's reporter asked for a hook or a tracker query. Listing the specs on other refs reaches the measured case (concurrent worktrees in one repo) directly. It costs one git call of well under a second, and it needs neither configuration nor network. [inferred]
