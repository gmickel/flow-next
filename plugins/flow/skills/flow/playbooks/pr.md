# Pull Request

Commit any spec on the same branch as the code before opening. When this PR completes a spec that sits in `.flow/specs/open/`, move it to `.flow/specs/` with `git mv` in a commit of its own, and fix any reference to the old path inside the repository in that commit. Do this before opening the PR, never while landing. Write the PR body directly, and never overwrite a body a person edited without asking.

## Body layout

Use these headings in order, omitting `## Shape` or `## Tradeoffs` when empty; always keep `## Needs you` (stating in one line when nothing is open):

- `## Why` — intent and user or operator outcome.
- `## Review focus` — where to start reading, one to three risky or surprising places to check closely, and the feedback wanted. Direct attention (for example, which commits are mechanical and which few files carry behaviour).
- `## Needs you` — open items as `- Open:` bullets (unmet or deferred requirements, unresolved design calls, unverified checks).
- `## Shape` — compact sketch of the new or changed public surface or key flow.
- `## What changes` — behaviour changes, requirement coverage, proof, docs, and the review line.
- `## Reading order` — logical review groups with safe-to-skim groups separated; no file lists and no line totals.
- `## Tradeoffs` — rejected alternatives and decisions made.

Under `## What changes`, describe the behaviour changes and state each spec requirement as met with evidence, deferred with a reason, or unmet (placing deferred and unmet items under `## Needs you`; this is a reporting target, so still open the PR). Name any unrequested changes explicitly and include live proof evidence (or "not verified live" for direct changes). List project documents mentioning touched files or names, updating each or explaining why not so none is left false. Close the section with one line naming the building model, the reviewing model (same or different family), the verdict, rounds, and findings declined.

## Mechanical changes and opening

Keep bulk mechanical changes (formatting, renames, generated output) in their own commit with the generating command in its message, and give each one line in the body naming the command and commit as safe to skim. Do not read bulk mechanical diffs to describe them: check with a per-file git summary and `git diff -w`, or sample a few files for a PR you did not write.

Push the branch and open the PR via the forge CLI, or `scripts/make-pr-gitlab.sh` / `scripts/make-pr-bitbucket.sh` beside the router. Move any linked tracker issue to in review with the PR link (`tracker.md`).
