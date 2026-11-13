# Bitbucket Cloud pull requests (gated reference)

> Read from workflow.md when the origin's forge is `bitbucket`. Everywhere else in land, the PR's
> number is its id and its head branch the source branch. The gates, their order, the verdicts and
> the terminal line stay as workflow.md says; only these reads and calls change.

Run bkt inside the checkout. bkt finds its host only through a context, so name a Bitbucket Cloud
one on every call, and take the repository from the origin remote:

```bash
BKT_CONTEXT=$(bkt context list --json | jq -r '[.contexts // [] | .[] | select(.host == "api.bitbucket.org")] | sort_by(.active != true) | .[0].name // empty' | tr -d '\r')
REPO=$(git remote get-url origin | sed -E 's#^[a-z+]+://[^/]+/##; s#^[^@/]*@?[^:/]+:##; s#\.git$##' | tr -d '\r')
```

No context stops `NEEDS_HUMAN` naming `bkt context create`. Below, `$PR` is the id, `$HEAD_SHA` the
full head SHA and `$BRANCH` the source branch.

- **Read the pull request.** `bkt --context "$BKT_CONTEXT" api "/repositories/$REPO/pullrequests/$PR"`:
  `state` (`OPEN`, `MERGED`, `DECLINED` or `SUPERSEDED`, the last two closed unmerged), `draft`,
  `source.branch.name`, `source.commit.hash` (Bitbucket's short head), `source.repository.full_name`,
  `destination.branch.name`, `links.html.href`, and once merged `merge_commit.hash`. A source
  repository other than `$REPO` (a fork's pull request) stops `NEEDS_HUMAN`.
- **Specs at the head.** Bitbucket keeps no pull request refs: `git fetch origin "refs/heads/$BRANCH"`
  and check that `FETCH_HEAD` starts with the short head; its full SHA is `$HEAD_SHA`, else the head
  moved: read again. Read `.flow/specs/*.json` and `.flow/tasks/` with `git ls-tree` and
  `git show "$HEAD_SHA:<path>"`, and the base from `origin/<destination>`, in place of the trees
  API. The selection rules are unchanged. On a merged replay the branch may be gone (the merge closes
  it): read the specs from the merged pull request's `merge_commit.hash` instead, after
  `git fetch origin "refs/heads/<destination>"`; a squash merge commit carries the head's changes.
- **Readiness.** For the selected spec, run `"$FLOWCTL" pilot snapshot --spec <spec-id> --json` in a
  detached worktree at `$HEAD_SHA` (the one repairs use), so the spec and its `branch_name` are the
  head's. Its `.selected.pr.open` `url` must be this pull request's `links.html.href` and
  `readiness.head_sha` the head you read; a moved head means read again (`RESOLVING` if it keeps
  moving), and no match at an unchanged head stops `NEEDS_HUMAN`. `readiness` holds `build` (the
  worst build status on this head: `FAILED`, `STOPPED`, `INPROGRESS` or `SUCCESSFUL`, null when none
  is reported), `merge_status` (`clean`, or the reason of the first of Bitbucket's own merge checks
  that fails), `approval` (`approved`, `changes_requested`, `none` or `unknown`), `squash_allowed`,
  `green` and `ready`. A pull request without a spec has no readiness read: stop `NEEDS_HUMAN`.
- **Conflicts and catch-up.** `merge_status: conflicts` stops `BLOCKED` naming the branch; any other
  failing merge check stops `NEEDS_HUMAN` naming it. Bitbucket squash-merges a branch that is behind
  its base, so there is no catch-up.
- **Threads.** Open comments go to resolve-pr exactly as on GitHub, from the detached worktree at
  `$HEAD_SHA`; its Bitbucket reference fetches and resolves them and pushes to `$BRANCH`.
- **Build.** `SUCCESSFUL` is green and `INPROGRESS` pending. `FAILED` gets the one focused fix when
  its cause can be found: the failing status's `url` and `description` from
  `bkt --context "$BKT_CONTEXT" api "/repositories/$REPO/commit/$HEAD_SHA/statuses?pagelen=100"`, or
  running that check in the detached worktree; otherwise, and for `STOPPED` or no build reported,
  stop `NEEDS_HUMAN`: a person runs, reruns or adds it.
- **Review.** `approval: changes_requested` stops `AWAITING_REVIEW`; `unknown` stops `NEEDS_HUMAN`.
  Land merges only on `ready: true`.
- **Patience.** The last authored push is the head commit's `date` from
  `bkt --context "$BKT_CONTEXT" api "/repositories/$REPO/commit/$HEAD_SHA"`.
- **Merge one layer.** An open pull request targeting `$BRANCH`
  (`bkt --context "$BKT_CONTEXT" api "/repositories/$REPO/pullrequests?q=$(jq -rn --arg b "$BRANCH" '"state=\"OPEN\" AND destination.branch.name=\"" + $b + "\"" | @uri')&pagelen=50"`;
  the state goes in the query, since Bitbucket ignores a `state` parameter beside `q`)
  or a draft stops `NEEDS_HUMAN`; `squash_allowed: false` (the branch forbids squash) stops
  `NEEDS_HUMAN` too, and land never picks another merge strategy. Bitbucket cannot pin a merge to a
  head: it ignores an expected SHA and merges the branch's head at that moment. So read the pull
  request and the readiness again immediately before the call, and merge only when both still name
  `$HEAD_SHA` with `ready: true`:
  `bkt --context "$BKT_CONTEXT" api "/repositories/$REPO/pullrequests/$PR/merge" -X POST -d '{"merge_strategy":"squash","close_source_branch":true}'`.
  Never `bkt pr merge`, auto-merge, or merge when the build passes. Then read the pull request
  again: only `state: MERGED` with a `merge_commit` confirms `MERGED`. When its `source.commit.hash`
  is not a prefix of `$HEAD_SHA`, the branch moved during the merge and Bitbucket merged commits
  land did not judge: report `MERGED` with both heads in the reason, so a person checks
  `<judged>..<merged>`.

The GitHub-only steps (merge queue, rulesets, `update-branch`, rerunning failed checks, stacks and
marking a draft ready) have no Bitbucket arm: where land needs one, it stops `NEEDS_HUMAN`. After
the merge, the tracker touchpoint runs as on GitHub; flowctl reads the merged pull request as
merge evidence.
