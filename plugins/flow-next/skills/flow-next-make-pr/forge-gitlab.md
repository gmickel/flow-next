# GitLab merge requests (gated reference)

> Read from workflow.md when preflight sets `FORGE=gitlab`. Everywhere else in this skill, "PR" means
> the merge request.

Preflight has checked glab's login and api scope on the origin host and set `FORGE`, `PR_READ` (the
bundled `make-pr-gitlab.sh`), `GITLAB_HOST` (the origin host with its port; glab rejects
`--hostname host:port`, so every glab call takes the host from this variable) and `ORIGIN_PROJECT`
(the project path). Carry all four into the create call, with `GITLAB_HOST` and `ORIGIN_PROJECT`
exported, as you carry `BASE_REF`. `make-pr-create.sh` then pushes and opens or updates the merge
request through `PR_READ` in place of gh, with the same body, draft rules and close as on GitHub.
An explicit `FLOW_PR_CREATE_CMD` still wins over the helper for creation.

- A draft is the `Draft: ` title prefix. `--update` replaces the description and keeps the draft
  state; `--update --ready` also drops `Draft:`, `[Draft]` and `(Draft)` from the title.
- There is no stack link: while a parent's merge request is open, the child targets its branch.
- Tracker finalize: the merge request's `created_at` is the `<PR-createdAt>`:
  `glab api "projects/$(jq -rn --arg v "$ORIGIN_PROJECT" '$v | @uri')/merge_requests/${PR_URL##*/}" | jq -r .created_at`.
- Finalize prints the merge request URL and the body-inspection line. Leave out the reviewer-feedback
  line: resolve-pr reads GitHub pull requests only.
- No-spec path: follow no-spec-path.md with `"$PR_READ" pr create --title <title> --body-file <file>
  [--draft] --base <branch> --head <branch>` in place of `gh pr create`. `--base` is required; without
  `--base`, use the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD` minus
  `origin/`). Under `--update`, run `"$PR_READ" pr edit <number> --body-file <file>`, with the number
  from `"$PR_READ" pr view --json number --jq .number`.
