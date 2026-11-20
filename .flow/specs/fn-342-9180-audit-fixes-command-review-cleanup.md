# 9.18.0 audit fixes: command review cleanup, criteria probe and Antigravity recipe

## Goal & Context

<!-- Source: 10% user / 65% [paraphrase] / 25% [inferred] -->

A cross-family audit of everything unreleased since 9.17.0 (fn-341 Antigravity host, fn-339 follow-ups, the refreshed Copilot and Cursor ladders) returned NEEDS_WORK on all three draws. The maintainer's rule is that nothing is released until found things that need fixing are fixed. This spec fixes the findings that hold up and records the ones that are declined, so 9.18.0 can ship.

The unattended failures these prevent: a review that runs a program from the checkout it is reviewing, and a reviewer process that keeps running after the review was cancelled or failed.

## Edge Cases & Constraints

- Every finding is checked against the code before it is fixed; one that does not reproduce is recorded as such and left alone. [inferred]
- No Windows Job Object or other new process-ownership mechanism. Where Windows cannot stop a helper whose wrapper already exited, the docs say so next to the existing note about fully detached helpers. [inferred]
- A skill contract change updates that skill's conduct checklist, and generated files are regenerated after the last flowctl edit. [inferred]

## Acceptance Criteria

- **R1:** The documented Antigravity review wrapper, and its Codex mirror copy, runs `agy` by an absolute path resolved outside the checkout under review, never by a bare name looked up after it has changed into that checkout. [paraphrase]
  Errors: `agy` not found, or found only inside the checkout → the wrapper fails with a clear message and no review runs.
- **R2:** The criteria check that detects a link written as a file runs git from the repository root, not from `.flow/`, so its program lookup is the same one the rest of flowctl already uses. [paraphrase]
  Errors: no error surface beyond the existing ones.
- **R3:** Interrupting a fan-out (Ctrl-C) stops every running command reviewer's process tree promptly; the interrupt does not wait for reviewers to finish or time out. [paraphrase]
  Errors: a tree that cannot be stopped is named in the output.
- **R4:** When a command reviewer's response is oversized, cleanup of its process tree finishes before the failure is returned, and a helper that could not be stopped is named in that failure. One owner does the cleanup; the reader only signals. [paraphrase]
  Errors: cleanup that exceeds its bound is reported as not stopped, never as stopped.
- **R5:** The link-as-file criteria error fires only while the working-tree file still holds the tracked link target. After the file is replaced with real content, including a document with headings and no criteria, the file is valid again. [paraphrase]
  Errors: an unreadable file keeps its existing error.
- **R6:** After a fan-out whose primary draw failed, the receipt carries no resumable session unless a successful draw on the primary label supplied one, even when the failed draw reported a session id. The failed draw stays in the draws list. [paraphrase]
  Errors: no session → validate and deep passes do not run, as today.
- **R7:** An explicit backend spec given to the validate and deep passes is checked by the same strict parser before it is compared with the receipt, so padded spellings are refused there too; and the schema's command pattern refuses a trailing newline under search semantics as well as full-match. [paraphrase]
  Errors: the refusal names the accepted form.
- **R8:** The implementation-review fan-out workflow text, and its mirror, say that a command review's session fallback stays on the primary label and what happens when no session exists, matching what the code does. [paraphrase]
  Errors: no error surface.
- **R9:** On Antigravity, setup does not label any reviewer as cross-family, because it cannot know which model family is writing. [paraphrase]
  Errors: other hosts' labels are unchanged.
- **R10:** The ladder tests pin the intended Cursor default and the head of the Copilot ladder by name, next to the invariant that the default is the first entry. [paraphrase]
  Errors: no error surface.
- **R11:** fn-339's first criterion is reworded to say what was built: the failure is for a tracked symbolic link that the checkout wrote as a plain file, detected from the index, not for any file whose text looks like a path. [inferred]
  Errors: no error surface.

## Boundaries

- No Windows Job Object, no new process-tracking mechanism, no new flowctl verb, config key, stage or receipt field. [inferred]
- No heuristic that rejects a regular criteria file because its text looks like a path. [inferred]
- Downstream documentation for Antigravity is done in the release walk, not here. [paraphrase]
- No change to ladder contents. [inferred]

## Decision Context

Two audit suggestions are declined. Tracking a Windows process tree with a Job Object was asked for so cleanup survives a wrapper that exits first; that is new machinery for a case the docs can state, like the existing limit for fully detached helpers. Rejecting any criteria file whose only content is a path was asked for on a literal reading of fn-339's wording; detecting the link from the index is the precise test and cannot misfire on a real file, so the wording is corrected instead.
