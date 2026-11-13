# Bitbucket Cloud pull requests (gated reference)

> Read from workflow.md when the snapshot's `forge` is `bitbucket`.

Resolve-pr does not read Bitbucket pull request comments yet. Stop before any fetch, fix, reply or
resolve, with `NEEDS_HUMAN: resolve-pr is not supported on Bitbucket Cloud yet` and the pull
request's URL, so the person handles its comments on Bitbucket. Under `mode:autonomous`, end with
`RESOLVE_PR_VERDICT=NEEDS_HUMAN threads=0 fixed=0 needs_human=0`.
