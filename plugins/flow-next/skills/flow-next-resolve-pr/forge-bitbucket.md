# Bitbucket Cloud pull requests (gated reference)

> Read from workflow.md when the Preamble reads `FORGE=bitbucket`. Every top-level pull request
> comment, inline or general, is a review thread here: it holds its replies and can be resolved.

The phases, triage, dispatch, validation and verdicts are workflow.md's; only the commands below
change. Run the scripts from inside the checkout: they take the workspace and repository from the
origin remote, and pick a bkt context on Bitbucket Cloud themselves.

- **Preamble:** in place of the gh check, `command -v bkt >/dev/null 2>&1 || { echo "bkt not
  installed. Install it from https://github.com/avivsinai/bitbucket-cli"; exit 1; }`. A missing
  login or context fails the first fetch with the commands that fix it; surface that as it is.
- **Phase 0:** a number is the pull request's id. A pull request URL
  (`https://bitbucket.org/<workspace>/<repository>/pull-requests/<id>`) gives its id and must name
  this checkout's repository: compare `<workspace>/<repository>`, ignoring case, with the path of
  `git remote get-url origin` (minus `.git`), and on a mismatch stop naming both, as for a GitHub
  URL. Comment URLs (targeted mode) are GitHub's: on Bitbucket, pass the id, the URL or nothing.
- **Phase 1:** with no target, `PR_NUMBER=$(bash "$SCRIPTS/get-bb-current-pr")` reads the current
  branch's open pull request (empty when there is none). Fetch with
  `FEEDBACK_JSON=$(bash "$SCRIPTS/get-bb-comments" "$PR_NUMBER")`: the same keys as
  `get-pr-comments`, every page, deleted comments left out. `pr_comments` and `review_bodies` are
  always empty. `isOutdated` is true when Bitbucket kept an inline comment on an earlier head
  because its line changed, so the resolver re-locates it by content.
- **Phase 5:** tell each resolver this is a Bitbucket pull request, and that where its
  instructions say `gh pr diff` or `gh pr view` it reads `git diff origin/<destination_branch>...HEAD`
  and `bash "$SCRIPTS/get-bb-pr" "$PR_NUMBER"` instead. A thread with no `path` is a general comment.
- **Phase 7:** push to the pull request's source branch, from `bash "$SCRIPTS/get-bb-pr"
  "$PR_NUMBER"`. On the branch, `git push`; from a detached checkout,
  `git push origin "HEAD:<source_branch>"`, or, when `source_repository` differs from
  `destination_repository` (a fork), `git push "https://bitbucket.org/<source_repository>.git"
  "HEAD:<source_branch>"`.
- **Phase 8:** as on GitHub, each thread gets its reply and then, unless the verdict is
  `needs-human`, is resolved:
  `echo "$REPLY" | bash "$SCRIPTS/reply-to-bb-comment" "$PR_NUMBER" "$FB_ID"`, then
  `bash "$SCRIPTS/resolve-bb-comment" "$PR_NUMBER" "$FB_ID"`. The reply goes under the thread's
  top-level comment. Resolving an already resolved comment exits 0; nothing to do.
- **Phase 9:** re-fetch with `get-bb-comments`.
- **Errors:** an HTTP 429 from bkt follows the rate-limit rule.
