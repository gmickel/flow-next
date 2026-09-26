# Land one pull request

## Read the named pull request

Read configuration once with `"$FLOWCTL" config get land --json`.
Only `land.mergeVerdictCommand` and `land.patienceMinutes` are used (defaults:
unset and 30). Existing configs may contain other `land.*` keys: print one
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
`status: done` at head, absent or not done at base, and at least one
`.flow/tasks/<spec-id>.*` entry whose tree SHA is absent from, or different in,
the base tree.
A closed spec has `status: done` and at least one
`.flow/tasks/<spec-id>.*.json` blob in the same tree. If any selected spec is
open, stop `BLOCKED`, reason `work not finished` naming every open selection;
change nothing. If the selected set is empty, stop `NO_WORK`, reason `no matching spec`.
Missing or malformed blobs, incomplete tree reads (including `truncated: true`), or API errors stop
`NEEDS_HUMAN`; they are not evidence of no match. Repeat this head-bound
selection after any head move. A merged replay reads its original head to
recover matching tracker links, without re-opening the landing gates; a lookup
failure there is a touchpoint failure and retains the confirmed `MERGED`.

## Resolve conflicts, threads, then CI

Read mergeability first. A conflict stops `BLOCKED` with the exact branch
needing a rebase. Unknown mergeability is `RESOLVING`, never permission to
merge. If behind its base, use server-side `gh pr update-branch <PR> --repo
<owner/repo>` without rebase; a refused catch-up is a conflict and stops
`BLOCKED` naming the branch needing a rebase. Re-read after catch-up.

Next enumerate all review threads with pagination. Open threads invoke
`flow-next:flow-next-resolve-pr <PR>` with `mode:autonomous`, bound to this PR and an
isolated checkout; the invoking checkout stays untouched. Resolver refusal
`NOT_RETRYABLE: artifact unchanged since last verdict` stops `NEEDS_HUMAN`.
Re-read the head
and threads afterward; unresolved threads stop `RESOLVING`.

Then inspect CI checks and failed logs. Pending checks stop `RESOLVING`.
Red CI in this PR's own code gets one focused fix in an isolated checkout,
verification, and an ordinary push. A flaky check gets one
`gh run rerun <run-id> --failed`; inspect prior attempts on this head first.
An identical second failure is not a flake and gets no second rerun.
If the fix does not turn CI green, stop `BLOCKED` naming the failing check;
if the new run is pending, report `FIXING_CI` and return to the caller.
External failures needing intervention stop `NEEDS_HUMAN` with their evidence.
Re-read all gates after a repair; never spend a second fix on the same failure
on a later invocation (use the PR's commits and check attempts as evidence).

## Authorize and gate the merge

Require green checks, a nonblocking `reviewDecision`, and zero unresolved
threads on the current head. `CHANGES_REQUESTED` or `REVIEW_REQUIRED` stops
`AWAITING_REVIEW`. No required reviews and no reviewer activity is allowed;
no bot comment or approval signal is required. A failed or incomplete read
stops safely. Honor any stricter repository instruction or branch protection.

Without this PR's current session merge authorization, stop
`AWAITING_REVIEW`, reason `merge-ready; authorization required` when ready.
When calling flow authorizes the merge without a human's in-session merge
authorization, require `land.patienceMinutes` since the last push. Use push
evidence; for a null push date use the head commit's earliest check-suite creation time, else its committer date. Before the
window expires, report `AWAITING_REVIEW` with `remaining_patience_seconds=<n>` (rounded up) and return;
the caller owns cadence. A human's current merge authorization waives the wait.

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
Paginate these reads. With open children, link the chain bottom-to-top using
`POST /repos/{owner}/{repo}/stacks` with `pull_requests` before merging.
Reuse an existing stack; read it again immediately before submitting.
Only the lowest open layer may merge: a higher layer stops `BLOCKED` naming
the lowest PR. Merge one layer per run; never merge a parent implicitly.
If stacks are unavailable, keep child-targeted branches on the ordinary path.
After the parent merges, inspect its children: a conflicted child is reported
as needing a rebase and land stops, retaining the confirmed parent merge.
A plain child still based on its parent needs a manual rebase onto the intended
base before its own landing; land never retargets it or resolves its conflicts.
Other stack errors stop `NEEDS_HUMAN`, not a silent fallback.

If the authorized PR is draft, mark it ready with `gh pr ready <PR> --repo <owner/repo>` and re-read
checks and review state before proceeding.
Refresh the full head SHA and all gates immediately before merge. A shortened
SHA is invalid. Ordinary PRs use `gh pr merge <PR> --repo <owner/repo>
--squash --match-head-commit <full-head-sha>`, adding `--delete-branch` only
after a successful fresh read proves no open PR targets the branch. The
explicit `--repo` keeps gh from switching or deleting a local branch.
Native stacks use `PUT /repos/{owner}/{repo}/pulls/{number}/merge-async` with
`merge_method=squash`, `merge_action=direct_merge`, and `sha=<full-head-sha>`;
never the ordinary merge call, auto-merge, or merge-queue enrollment.
Observe its returned status/UUID in memory; pending is `RESOLVING`, not success.
After either merge call, re-read the exact PR: only `MERGED` with a merge
commit confirms success, including after a command error. Never store polling state.
A moved head refuses the merge: re-read the PR and gates, report `RESOLVING`,
and do not retry with a substituted SHA. Other refusals report `BLOCKED`.

On a native stack, after confirming the merge, freshly verify no open PR has
the merged branch as base before deleting its remote ref with a separate
`DELETE /repos/{owner}/{repo}/git/refs/heads/{branch}` call (encode the ref).
If children still target it, or the read fails, keep the branch and report it.
A deletion failure leaves the merge confirmed; include it in the reason.

## After confirmed merge

Write nothing to the repository: no checkout, commit, push, or state file.
For each matching spec, run the tracker touchpoint if the bridge is active
and current restrictions permit it; `tracker.perEvent.land.merged` does not
gate the terminal status. Use the existing `flowctl_tracker` API in memory
with `python -B` to prevent bytecode writes:
use the head-read spec and bridge config, durable-check with `wire.parent_read`,
normalize with `status.policy.flow_to_normalized` using this exact PR's
confirmed merge evidence, and use `status.policy.decide`. Apply an allowed
transition with `status.providers.apply_status` and
`resolve_verb.bound_executor(config, executor.execute)`. Preserve configured
status IDs, terminal-state policy and completion-review gating. Do not use
`tracker sync` or `tracker status`: they write local claims and receipts.
Read helper signatures from the bundled scripts; do not reconstruct provider
requests. Keep inputs/results in memory, including `evidence=<merge-commit-sha>`;
no local fold, timestamp write, or comment is needed for the terminal touchpoint.
A tracker failure or deferred transition is reported with the merge commit
in the reason and never changes `MERGED`. Reruns repeat only this touchpoint,
using fresh merge evidence; never infer a merge from locally closed specs.
Print one final `LAND_VERDICT=MERGED` line with the PR URL and merge commit,
including any tracker failure, skipped restriction, or remaining child rebase.
