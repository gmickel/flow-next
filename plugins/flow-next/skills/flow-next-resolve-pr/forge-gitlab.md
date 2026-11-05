# GitLab merge requests (gated reference)

> Read from workflow.md when the Preamble reads `FORGE=gitlab`. Everywhere else in this skill,
> "PR" means the merge request, a review thread is a resolvable MR discussion, and a PR comment
> is an MR note that is not resolvable.

The phases, triage, dispatch, validation and verdicts are workflow.md's; only the commands below
change. Run them from inside the checkout: glab takes the host and the project (`projects/:id`)
from the origin remote. With an SSH origin whose GitLab web port is not the default, export
`GITLAB_HOST=<host>:<port>` first.

- **Preamble:** in place of the gh check, `glab auth status >/dev/null 2>&1 || { echo "glab not
  authenticated. Run: glab auth login"; exit 1; }`. Replying and resolving need a token with `api`
  scope; a narrower one fails at the first reply with GitLab's 403, which you surface as it is.
- **Phase 0:** a number is the merge request's iid (`!13` is 13). A merge request URL
  (`<project URL>/-/merge_requests/<iid>`) gives its iid and must name this checkout's project:
  compare the part before `/-/merge_requests/`, ignoring case, with
  `glab api "projects/:id" | jq -r .web_url`, and on a mismatch stop naming both, as for a GitHub
  URL. Comment URLs (targeted mode) are GitHub's: on GitLab, pass the iid, the URL or nothing.
- **Phase 1:** with no target, `glab mr view --output json | jq -r .iid` reads the current
  branch's merge request. Fetch with
  `FEEDBACK_JSON=$(bash "$SCRIPTS/get-mr-discussions" "$PR_NUMBER")`: the same keys as
  `get-pr-comments`, every page, system notes left out. `review_bodies` is always empty, and
  `isOutdated` is true when a discussion sits on an older head than the merge request's, so the
  resolver re-locates it by content.
- **Phase 5:** tell each resolver this is a GitLab merge request, and that where its instructions
  say `gh pr diff` or `gh pr view` it reads `git diff origin/<target_branch>...HEAD` and the
  merge request below instead.
- **Phase 7:** push to the merge request's source branch. Read `source_branch`, `target_branch`,
  `source_project_id` and `project_id` from `glab api "projects/:id/merge_requests/$PR_NUMBER"`. On
  the branch, `git push`; from a detached checkout, `git push origin "HEAD:<source_branch>"`, or,
  when the source project differs (a fork), push to
  `glab api "projects/$SOURCE_PROJECT_ID" | jq -r .http_url_to_repo`.
- **Phase 8:** as on GitHub, a review thread gets its reply and then, unless the verdict is
  `needs-human`, is resolved:
  `echo "$REPLY" | bash "$SCRIPTS/reply-to-mr-discussion" "$PR_NUMBER" "$FB_ID"`, then
  `bash "$SCRIPTS/resolve-mr-discussion" "$PR_NUMBER" "$FB_ID"`. A PR comment gets a new note:
  `glab api -X POST "projects/:id/merge_requests/$PR_NUMBER/notes" -f "body=$REPLY"`. Never reply
  inside the note's own discussion: that turns it into an unresolved thread, which blocks a merge
  where the project requires every thread resolved.
- **Phase 9:** re-fetch with `get-mr-discussions`.
- **Errors:** an HTTP 429 from glab follows the rate-limit rule. Resolving an already resolved
  discussion succeeds again; nothing to do.
