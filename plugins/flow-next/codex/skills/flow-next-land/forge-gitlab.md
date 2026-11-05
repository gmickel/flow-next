# GitLab merge requests (gated reference)

> Read from workflow.md when the origin's forge is `gitlab`. Everywhere else in land, "PR" means the
> merge request, its number the iid, and its head branch the `source_branch`. The gates, their
> order, the verdicts and the terminal line stay as workflow.md says; only these reads and calls
> change.

Run glab inside the checkout, where `projects/:id` resolves from the origin remote (export
`GITLAB_HOST` with the web port when the origin is an SSH remote). Below, `$MR` is the iid,
`$HEAD_SHA` the full head SHA and `$BRANCH` the source branch.

- **Read the merge request.** `glab api "projects/:id/merge_requests/$MR"`: `state` (`opened`,
  `merged`, `closed`; `locked` is mid-merge, so read it again), `sha`, `source_branch`,
  `target_branch`, `web_url`, `head_pipeline`, and once merged `merge_commit_sha`, else
  `squash_commit_sha`.
- **Specs at the head.** `git fetch origin "refs/merge-requests/$MR/head"` (GitLab keeps every
  merge request's head there, a fork's too) and check that `FETCH_HEAD` is `$HEAD_SHA`, else the
  head moved: read again. Read `.flow/specs/*.json` and `.flow/tasks/` with `git ls-tree` and
  `git show "$HEAD_SHA:<path>"`, and the base from `origin/<target_branch>`, in place of the trees
  API. The selection rules are unchanged.
- **Readiness.** For the selected spec, run `"$FLOWCTL" pilot snapshot --spec <spec-id> --json` in
  a detached worktree at `$HEAD_SHA` (the one repairs use), so the spec and its `branch_name` are
  the head's. Its `.selected.pr.open` `url` must be this merge request's `web_url` and
  `readiness.head_sha` the head you read. A moved head means read again (`RESOLVING` if it keeps
  moving); at an unchanged head with no match (a fork's merge request, which the snapshot does not
  list, or a spec whose `branch_name` names another branch) stop `NEEDS_HUMAN`. `readiness` holds
  `merge_status` (GitLab's detailed merge status), `pipeline` (the head pipeline's status for this
  head, including a merged-results pipeline on GitLab's merge commit of it, null when none), `approval` (`approved`, `required` or `unknown`), `squash_allowed`, `green`
  and `ready`. A merge request without a spec has no readiness read: stop `NEEDS_HUMAN`.
- **Conflicts and catch-up.** `merge_status: conflict` stops `BLOCKED` naming the branch. GitLab
  merges a branch that is behind its base, so there is no catch-up; `need_rebase` (the project
  merges fast-forward only) stops `NEEDS_HUMAN`. `checking`, `unchecked` and `preparing` are
  `RESOLVING`.
- **Threads.** Open discussions go to resolve-pr exactly as on GitHub, from the detached worktree
  at `$HEAD_SHA`; its GitLab reference fetches and resolves them and pushes to `$BRANCH`.
- **Pipeline.** `success` is green. `created`, `waiting_for_resource`, `preparing`, `pending`,
  `running` and `scheduled` are pending checks. `failed` gets the one focused fix: list the failed
  jobs with `glab api "projects/:id/pipelines/$PIPELINE_ID/jobs?scope=failed"` (`$PIPELINE_ID` is
  `head_pipeline.id`) and read each log with `glab api "projects/:id/jobs/$JOB_ID/trace"`. A
  failure that looks flaky, `manual`, `canceled`, `skipped`, or no pipeline for this head stops
  `NEEDS_HUMAN`: a person runs, retries or starts it.
- **Review.** `approval: required` stops `AWAITING_REVIEW`. Land merges only on `ready: true`.
- **Patience.** The last authored push is the head pipeline's `created_at`, else the head commit's
  committer date.
- **Merge one layer.** An open merge request targeting `$BRANCH`
  (`glab api -X GET "projects/:id/merge_requests" -f state=opened -f "target_branch=$BRANCH"`, a
  field so glab encodes the branch name) or a draft stops
  `NEEDS_HUMAN`; `squash_allowed: false` (the project forbids squash) stops `NEEDS_HUMAN` too, and
  land never picks another merge method. With a fresh `ready: true` for `$HEAD_SHA`:
  `glab api -X PUT "projects/:id/merge_requests/$MR/merge" -F squash=true -F should_remove_source_branch=true -f "sha=$HEAD_SHA"`.
  Never `glab mr merge`, auto-merge, or merge when the pipeline succeeds. HTTP 409 (`SHA does not
  match HEAD of source branch`) is a moved head: `RESOLVING`, never a retry with another SHA. Then
  read the merge request again: only `state: merged` with a merge commit confirms `MERGED`.

The GitHub-only steps (merge queue, rulesets, `update-branch`, rerunning failed checks, stacks and
marking a draft ready) have no GitLab arm: where land needs one, it stops `NEEDS_HUMAN`. After the
merge, the tracker touchpoint runs as on GitHub; flowctl reads the merged merge request as merge
evidence.
