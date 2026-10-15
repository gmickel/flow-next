# Land one pull request

## Read the named pull request

Read configuration once with `"$FLOWCTL" config get land --json`.
Only `land.mergeVerdictCommand` and `land.patienceMinutes` are used (defaults:
unset and 10). Existing configs may contain other `land.*` keys: print one
notice naming all ignored keys and continue; do not rewrite the config.

With no pull request, stop `NEEDS_HUMAN`, reason `no pull request`.
Resolve the exact PR with `gh pr view <PR> --repo <owner/repo>`; read its URL,
state, `headRefOid`, `headRefName`, head repository, base, and merge commit.
An unreadable or ambiguous target stops `NEEDS_HUMAN` with the lookup error.
A closed unmerged PR stops `NO_WORK`, reason `closed unmerged`.
An already merged PR stops the landing path, reason `already merged`:
repeat only the configured tracker touchpoint below, then report `MERGED`.
Do not repair, merge again, or delete a branch on that replay.

Read every `.flow/specs/*.json` blob at full `headRefOid` from the PR's
head repository using the recursive git trees API (`recursive=1`), never local state.
Select every spec whose `branch_name` equals `headRefName`; several matches are valid.
If none match, read the `baseRefName` tree from the base repository and select specs with
`status: done` at head, absent or not done at base, and either a `retired` record at head or at least one
`.flow/tasks/<spec-id>.*` entry whose tree SHA is absent from, or different in,
the base tree; also select any spec not done at head whose task entries the PR changes that
way, so the open-work stop below catches unfinished work built on another branch.
A closed spec has `status: done` and either a `retired` record or at least one
`.flow/tasks/<spec-id>.*.json` blob in the same tree. If any selected spec is
open, stop `BLOCKED`, reason `work not finished` naming every open selection;
change nothing. An empty selected set is a pull request opened without a spec (make-pr's no-spec
path): land it through the same gates below, with no spec to check and no tracker touchpoint.
Missing or malformed blobs, incomplete tree reads (including `truncated: true`), or API errors stop
`NEEDS_HUMAN`; they are not evidence of no match. Repeat this head-bound
selection after any head move. A merged replay reads its original head to
recover matching tracker links, without re-opening the landing gates; a lookup
failure there is a touchpoint failure and retains the confirmed `MERGED`.

## Resolve conflicts, threads, then CI

Read mergeability first. A conflict stops `BLOCKED` with the exact branch needing a rebase. Unknown
mergeability is `RESOLVING`, never permission to merge. A PR missing base commits
(`gh api repos/<owner/repo>/compare/<base>...<head>` reports `behind_by` above 0; unreadable: `RESOLVING`)
is caught up last, below, required by the base or not; a stack layer on a parent branch is caught up here.

Next enumerate all review threads with pagination. Open threads invoke
`$flow-next-resolve-pr <PR>` with `mode:autonomous`, bound to this PR and an isolated checkout:
a detached worktree at the PR head (`git worktree add --detach <dir> <headRefOid>`, removed afterwards)
that pushes by name (`git push <head repository URL> HEAD:<headRefName>`). Resolver refusal
`NOT_RETRYABLE: artifact unchanged since last verdict` stops `NEEDS_HUMAN`. Re-read the head and threads
afterward. `RESOLVE_PR_VERDICT=NEEDS_HUMAN` (a thread the resolver handed to a person) stops
`NEEDS_HUMAN` with its `NEEDS_HUMAN:` lines, so the run asks once instead of re-running on the same
thread each tick; other unresolved threads stop `RESOLVING`.

Then inspect CI checks and failed logs. Pending checks stop `RESOLVING`. Red CI in this PR's own code
gets one focused fix in an isolated checkout (the same detached worktree), verification, and a push to
the PR branch. A flaky check gets one `gh run rerun <run-id> --failed`; inspect prior attempts on this
head first. An identical second failure is not a flake and gets no second rerun. If the fix does not
turn CI green, stop `BLOCKED` naming the failing check; if the new run is pending, report `FIXING_CI`
and return to the caller. Red CI on a head whose only commits since its last green head are catch-ups
stops `BLOCKED` naming the base move, with no repair. External failures needing intervention stop
`NEEDS_HUMAN` with their evidence. Re-read all gates after a repair; never spend a second fix on the
same failure on a later invocation (use the PR's commits and check attempts as evidence).

## Authorize and gate the merge

Require green checks, a nonblocking `reviewDecision`, and zero unresolved threads on the current head.
`CHANGES_REQUESTED` or `REVIEW_REQUIRED` stops `AWAITING_REVIEW`. Absent reviews are fine; a failed or
incomplete read stops safely. Honor any stricter repository instruction or branch protection.

Without this PR's current session merge authorization, stop `AWAITING_REVIEW`, reason
`merge-ready; authorization required` when ready. When calling flow authorizes the merge without a
human's in-session merge authorization, require `land.patienceMinutes` since the last authored push (the
newest commit that is not a catch-up, below), so review bots can post. Use push evidence; with no push
date use that commit's earliest check-suite creation time, else its committer date. Before the window
expires, report `AWAITING_REVIEW` with `remaining_patience_seconds=<n>` (rounded up) and return; the
caller owns cadence. A human's current merge authorization waives the wait.

Catch up last: only when being behind alone stops the merge, before the verdict command. A base whose
effective rules (`gh api repos/<owner/repo>/rules/branches/<base>`) include `merge_queue` is never caught up
(unreadable: none). A catch-up is a two-parent commit by committer `web-flow` whose second parent is from
the base. Walk first parents from the head with `gh api repos/<owner/repo>/commits/<sha>` to the first other
commit; a failed or incomplete read is `RESOLVING`, never an authored commit. Two catch-ups already on top
stop `NEEDS_HUMAN` naming the moving base. Otherwise
`gh api -X PUT repos/<owner/repo>/pulls/<PR>/update-branch -f expected_head_sha=<head>`: a moved head is
`RESOLVING`, another refusal `BLOCKED` naming the branch; then report `RESOLVING`.

When set, run `land.mergeVerdictCommand` once per invocation, only when all
other gates allow merging, with a 600-second host-tool bound. Supply
`FLOW_HEAD_SHA`, `FLOW_BASE_REF`, `FLOW_PR_NUMBER`, and `FLOW_SPEC_ID` (the
single matching ID, or empty for multiple matches; supply all in
`FLOW_SPEC_IDS`, space-separated). Run from the invoking repository without
changing its checkout; the command must judge the supplied remote head.
Any non-zero exit stops `NEEDS_HUMAN`: a missing, unexecutable, or timed-out
command is a refusal too. Include exit/error evidence. Do not rerun it after
a head race in this invocation; re-read and return `RESOLVING` for fresh gating.

## Merge one layer

Read open children targeting this PR's head branch and its native stack.
Paginate these reads. Skip [references/stacks.md](references/stacks.md) only when both reads
succeed completely and find no open children and no native stack; otherwise (children, a stack,
or any read error) read it and follow it here, at the merge call, and after the merge.

If the authorized PR is draft and flow authorized the merge without a human's in-session merge
authorization, stop `NEEDS_HUMAN` naming its open items: the draft marks a call the run left for a
person. With a human's current authorization, mark it ready with `gh pr ready <PR> --repo
<owner/repo>` and re-read checks and review state before proceeding.
Refresh the full head SHA and all gates immediately before merge. A shortened
SHA is invalid. Ordinary PRs use `gh pr merge <PR> --repo <owner/repo>
--squash --match-head-commit <full-head-sha>`, adding `--delete-branch` only
after a successful fresh read proves no open PR targets the branch; `--repo` keeps local branches safe.
After either merge call, re-read the exact PR: only `MERGED` with a merge
commit confirms success, including after a command error. Never store polling state.
A PR left open because the merge call added it to a merge queue (the call says so) reports
`QUEUED`, not a failure: run no post-merge step, and tell the person to run `/flow-next:land <PR>`
again once it merges, which replays the tracker touchpoint as an already merged PR.
A moved head refuses the merge: re-read the PR and gates, report `RESOLVING`,
and do not retry with a substituted SHA. Other refusals report `BLOCKED`.

## After confirmed merge

Write nothing to the repository: no checkout, commit, push, or state file.
Run `"$FLOWCTL" sync active --json`. Only when it reads `active: false`: no tracker touchpoint.
Otherwise, including an error: read [references/tracker-merged.md](references/tracker-merged.md)
and run it for each matching spec.
A tracker failure or deferred transition is reported with the merge commit
in the reason and never changes `MERGED`. Reruns repeat only this touchpoint,
using fresh merge evidence; never infer a merge from locally closed specs.
Print one final `LAND_VERDICT=MERGED` line with the PR URL and merge commit,
including any tracker failure, skipped restriction, or remaining child rebase.
