# Bitbucket Cloud pull requests (gated reference)

> Read from workflow.md when preflight sets `FORGE=bitbucket`.

Preflight has checked that bkt holds a Bitbucket Cloud login that reads the origin repository, and
set `FORGE`, `PR_READ` (the bundled `make-pr-bitbucket.sh`) and `ORIGIN_PROJECT`
(`<workspace>/<repository>`). Carry all three into the create call, with `ORIGIN_PROJECT` exported,
as you carry `BASE_REF`. `make-pr-create.sh` then pushes and opens or updates the pull request
through `PR_READ` in place of gh, with the same body, draft rules and close as on GitHub. An
explicit `FLOW_PR_CREATE_CMD` still wins over the helper for creation.

- `"$PR_READ" pr create` refuses a branch that already has an open pull request, or whose pull
  requests it cannot read: Bitbucket answers such a create with the open one, its title and
  description overwritten. Use `--update` for an open pull request.
- `--draft` opens a draft. `--update` replaces the description and keeps the draft state;
  `--update --ready` also marks the draft ready.
- There is no stack link: while a parent's pull request is open, the child targets its branch.
- Tracker finalize: `"$PR_READ" pr view --json createdAt --jq .createdAt` is the `<PR-createdAt>`.
- No-spec path: follow no-spec-path.md with `"$PR_READ" pr create --title <title> --body-file <file>
  [--draft] --base <branch> --head <branch>` in place of `gh pr create`. `--base` is required; without
  `--base`, use the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD` minus
  `origin/`). Under `--update`, run `"$PR_READ" pr edit <number> --body-file <file>`, with the number
  from `"$PR_READ" pr view --json number --jq .number`.
