---
title: "Skill fences that degrade only without set -e: masked failures in make-pr chain "
date: "2026-09-13"
track: bug
category: runtime-errors
module: plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md
tags: [set-e, bash-fence, fixtures, make-pr, chain, stack]
problem_type: runtime-error
symptoms: stack-link POST failure aborted the fence before its one-line degrade; fixtures without set -e stayed green
root_cause: VAR=$(cmd); rc=$? under set -e exits before rc is read; runner omitted the preamble's shell options
resolution_type: fix
---

## Problem
The make-pr stack-link fence captured a failing `gh api` POST as `LINK_OUT=$(gh api ...); LINK_RC=$?` and then branched on `LINK_RC` to print the documented one-line degrade. The make-pr workflow preamble runs every fence under `set -e`, so a failed POST aborted the fence before `LINK_RC` was assigned: the PR existed, the finalize tail never ran, and no diagnostic was printed. The consumer fixture runner executed the fence without `set -e`, so 25 green tests never saw it. The same review round found two siblings of the "swallowed failure" class in the merged-parent rewrite: `git fetch ... || true` before enabling a rebase onto a possibly stale chain base, and an `ls-remote | cut` pipeline whose exit status was masked so a failed remote read read as "branch not on origin".

## What Didn't Work
Testing the fences in a bash runner without the production shell options. Behaviourally the fence looked correct; only the `set -e` interaction broke it.

## Solution
`plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md` §4.6c: every fallible call inside the stack-link fence sits in a conditional (`if LINK_OUT=$(gh api ...); then LINK_RC=0; fi`, `OWNER_REPO=$(...) || { ...; }`). `workflow.md` §0.3/§0.6b: the chain-base fetch must succeed before `CHAIN_REWRITE=1`, and `REMOTE_LS=$(git ls-remote ...) || exit 2` is checked before parsing. `plugins/flow-next/tests/test_chain_consumer_fixtures.py` `ConsumerWorld.run_rc` prepends `set -e` so fences run under the production shell options.

## Prevention
Any fixture runner that slices bash fences out of skill prose must prepend the same shell options the skill's preamble sets (`set -e` for make-pr). In a `set -e` fence, never write `VAR=$(cmd); rc=$?` for a call that is allowed to fail; use `if VAR=$(cmd); then` or `VAR=$(cmd) || handler`. Treat `|| true` before a state-changing step (rebase, push) and `cmd | cut` on a remote read as findings: a masked failure becomes a wrong branch tip or a skipped lease.
