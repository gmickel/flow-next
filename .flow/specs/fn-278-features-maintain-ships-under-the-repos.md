# Features maintain ships under the repo's own naming rules and host, and keeps proven edits when shipping fails

## Conversation Evidence

- Issue #495 (reporter CWayman): maintain's ship step "can only finish on a GitHub-hosted repo whose branch and commit names are free-form". On their Bitbucket repo a commit hook rejects branches and commits without a Jira key, so "a maintain pass does all the expensive work ... then fails at the ship step and throws the proven edits away". [user]
- make-pr already routes its create call through `FLOW_PR_CREATE_CMD`; maintain does not. [user]
- The issue proposes three `features.maintain` config keys (`ship`, `branchTemplate`, `commitTemplate`) plus a `--ticket` argument. [user]
- Maintainer: "if valid, best, agentic fix for both". [user]

## Goal & Context

Maintain's `CHANGED` path cuts a fixed branch name, commits with a fixed message, pushes, and opens the PR with a bare `gh pr create`. A repo whose hooks require a ticket key in branch and commit names, or whose host is not GitHub, cannot finish a pass. Any failure there ends `BLOCKED`, and `BLOCKED` restores every uncommitted map edit to HEAD, which throws away the proven corrections. [paraphrase]

The fix follows "Agent first": the agent reads the repo's naming rules and names the branch and commit to fit them. It asks only for a value it cannot know, such as a ticket key, and asks at entry, before any proof work. It opens the PR through the same create seam make-pr uses. A failure after the proofs keeps the proven edits. [inferred]

## Architecture & Data Models

- **Entry gate.** Before any inspection, the agent reads the repo's branch and commit naming rules (project instructions, contributing docs, commit hooks). When they need a value the run cannot know (a ticket key), it asks for it now. When nobody can answer (a host loop), it ends `BLOCKED` at entry, naming the missing value. [paraphrase]
- **Naming.** The branch and commit message follow those rules. With no rules, today's `chore/features-maintain-<date>-<run-id>` branch and `chore(features): maintain pass` message stay the defaults. [paraphrase]
- **PR creation.** The create call is `${FLOW_PR_CREATE_CMD:-gh pr create}`, with the arguments and PR-URL output contract make-pr documents. When no create command can reach the host (not GitHub and no `FLOW_PR_CREATE_CMD`), the pass stops after the push and ends `CHANGED`. The `reason` names the pushed branch and says the PR was not opened. [paraphrase]
- **Less shipping on request.** A user who asks at invocation to only commit, or to leave the edits uncommitted, gets that. The run ends `CHANGED`, with the `reason` saying where the edits are (the local branch, or the working tree plus the files to stage). [paraphrase]
- **Failure keeps proven edits.** A refused commit, a failed push or a failed PR create after the proofs ends `BLOCKED` without restoring anything. The edits stay on the local branch or in the working tree, and the `reason` names the step that failed and where the edits are. The restore-to-HEAD rule still applies to blocks before or during the proofs, and to a base that moved during the pass (those proofs describe the wrong code). [paraphrase]

## API Contracts

The terminal grammar is unchanged: `FEATURES_VERDICT=<CLEAN|CHANGED|BLOCKED> features=<n> reason="<one line>"`. [paraphrase]

## Edge Cases & Constraints

- A formatter or hook that rewrites files at commit time still requires the edited files to be re-read, as today. [inferred]
- The next run's entry gate still requires clean owned paths. Edits kept after a failed ship must be committed, shipped or stashed by the human first, and the `BLOCKED` reason says so. [inferred]

## Acceptance Criteria

- **R1:** Maintain's entry gate tells the agent to read the repo's branch and commit naming rules and to obtain any value it cannot know (a ticket key) before Phase 1. Errors: no one to answer ends `BLOCKED` at entry, naming the value. [paraphrase]
- **R2:** Phase 6 names the branch and commit per those rules, with today's names as the default when the repo states none (no error surface beyond R1). [paraphrase]
- **R3:** Phase 6 opens the PR through `${FLOW_PR_CREATE_CMD:-gh pr create}`. Errors: with no reachable create command, the pass ends `CHANGED` after the push, naming the branch and the unopened PR. [paraphrase]
- **R4:** A user request at invocation to only commit, or to leave the edits uncommitted, is honoured, and the run ends `CHANGED` saying where the edits are (no error surface beyond R3). [paraphrase]
- **R5:** A commit, push or PR-create failure after the proofs ends `BLOCKED` without restoring the proven edits, naming the failed step and where the edits are. Blocks before the ship step, and a moved base, keep today's restore. [paraphrase]
- **R6:** The features skill contract tests assert R1, R3 and R5 in maintain's prose, and the features docs describe the ship behaviour. [paraphrase]

## Boundaries

- No `features.maintain.*` config keys, no template placeholders and no `--ticket` argument; the agent reads the repo's rules. [paraphrase]
- No forge adapter; that stays with #462. [user]
- Seed mode is unchanged. [inferred]

## Decision Context

The issue's three config keys and template placeholders would encode, as schema, naming rules the repo already states for humans. An agent that reads those rules names the branch correctly without a schema. Asking at entry keeps the issue's key protection, a missing ticket stopping the run before the proofs, without a template language. The create seam reuses make-pr's existing contract. Keeping proven edits on a failed ship helps every host, including a GitHub push that fails transiently. [inferred]

## Strategy Alignment

Serves "Agent first": the agent names the ship to fit the repo's rules instead of filling templates. [strategy:agent-first]

## Strategy Conflicts

None found.
