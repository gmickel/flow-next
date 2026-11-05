# No-spec path (gated reference)

> Read from workflow.md only when preflight exits 4 (`NO_SPEC`). After a `FORGE=` line, the forge's
> reference (`forge-<FORGE>.md`) gives the commands that replace `gh pr create` and `gh pr edit` here.

Never create a spec to open a pull request. Under `--dry-run`, write the body below, print it and
stop, with no branch, commit or push. Otherwise, on the default branch, first create a branch
named for the change, and commit the change if it is not committed yet (`git add -- <files you
changed>`). Write the session's handoff (what changed, how it was verified, open items and
follow-ups) to a temporary body file, push, and run `gh pr create` with a one-line title and that
body file; add `--draft` for `--draft` or when the handoff lists an open item (a call left for
the person, an open QA finding; follow-ups alone never draft), and `--base` when given. Under `--update`, run
`gh pr edit` with the body file instead. Print the PR URL.
