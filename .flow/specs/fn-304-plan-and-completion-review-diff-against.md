# Plan and completion review diff against the spec's own base

## Goal & Context

[paraphrase] Plan review and completion review default their diff base to a literal `main` on every review backend. On a repository whose default branch is `master` both fail before dispatch (`cannot resolve review snapshot: main...HEAD`, issue #538). On a spec whose work lands on a branch other than the default branch (a release integration branch, a chained parent, a `flow --goal` integration branch), completion review would judge the wrong diff even once the default branch is found: it would include every earlier child of that branch (issue #569). The other review commands already resolve the repository's default branch; work already resolves the spec's base and keeps it for its own gates, but no review reads it.

Both issues were reported by @DanielKillenberger.

## Architecture & Data Models

[paraphrase] One base resolution for a spec's reviews:

- **Plan review** uses an explicit `--base`, else the repository's default branch, resolved the same way the other review commands resolve it.
- **Completion review** uses the first that applies: an explicit `--base`; the base branch work recorded for this spec's run; the chain parent's branch; the repository's default branch.
- **Work records the base branch name** for the spec it runs, beside the merge-base SHA it already keeps. A review computes the merge-base from that branch at review time, so a child rebased onto a newer integration branch does not see commits from other children.

[inferred] Ownership: the recorded base belongs to one spec's run. A record written for a different spec is never used for this spec's review; it falls through to the next step. A recorded branch that no longer resolves falls through the same way rather than failing the review.

## API Contracts

[paraphrase] Every review backend's `plan-review` and `completion-review` command accepts an omitted `--base` and resolves it as above; an explicit `--base` keeps its current meaning. The host completion-review workflow resolves its diff base in the same order when the caller passes no explicit base. Receipts keep recording the base they reviewed.

## Edge Cases & Constraints

- [inferred] No default branch resolvable and no other source: the review fails with the existing "no default branch resolved ... pass --base <ref>" error, before any round is reserved.
- [inferred] An explicit `--base` (or host `BASE_COMMIT`) that does not resolve still fails closed; it never falls back to another base.
- [inferred] All supported review backends behave the same (Cross-platform parity).

## Acceptance Criteria

- **R1:** [paraphrase] On a repository whose default branch is `master` (no `main`), plan review and completion review with no `--base` resolve `master` and run, on every backend. Errors: no resolvable default branch and no other source → the existing default-branch error naming the candidates tried, no round reserved.
- **R2:** [paraphrase] Completion review with no `--base`, on a spec whose work run recorded a base branch, diffs against the merge-base of that branch and HEAD computed at review time. A test shows a child spec on an integration branch that also holds another child's commits reviews only its own commits. Errors: a record for a different spec, or a recorded branch that no longer resolves, falls through to the next source.
- **R3:** [paraphrase] Completion review with no `--base` and no run record, on a chained spec, diffs against the chain parent's branch. Errors: parent branch unresolvable → falls through to the default branch.
- **R4:** [paraphrase] An explicit `--base` on either command still wins over every other source and fails closed when it does not resolve (no error surface beyond today's).
- **R5:** [paraphrase] The host completion-review workflow resolves its diff base in the R2-R4 order and no longer names a literal `main`/`master` fallback.
- **R6:** [paraphrase] Work records the base branch name for the spec it runs, alongside the merge-base SHA it already records; work's existing consumers of the SHA are unchanged (no error surface beyond the existing branch-setup fence).

## Boundaries

- No `review.base` config key.
- The base is not persisted on the spec record (no `base_branch` field).
- [inferred] No separate goal-branch derivation in flowctl: a goal child's work run is dispatched with the goal integration branch as its base, so R2 covers it.
- [inferred] Implementation review's base resolution is unchanged.

## Decision Context

[paraphrase] A config key and a persisted spec field were proposed in #569 and left out: the chain parent, the work run's recorded base and the default branch cover the reported setups (a release integration branch with children run via `--base`, and goal mode). They would only matter for a completion review run by hand in a cold session after `work --base`; revisit if that is reported.

[inferred] Goal-branch derivation was dropped from the resolution order: flowctl has no data link from a child to its goal (the goal depends on its children, and where children land is recorded in the goal's log prose), so any derivation would be a heuristic. Goal children run work with `--base=goal/<branch_name>`, which R2 records.

## Strategy Alignment

[strategy:Cross-platform parity] The same resolution on every review backend, including host.
