# Review

## Dispatch

Send review to another model family through `orchestrate.md`. If a named reviewer cannot be reached, stop and say so; never substitute a reviewer silently. When no preference is stated and no other family is reachable, the same family reviews and that fact goes on the PR's review line. A reviewer from the builder's own vendor, the builder's own model included, is a same-family review wherever its name appeared; never report it as another family.

On the first round of a change review, use one reviewer when the change is small, stays in one area, and touches no shared state, concurrency, security, or data layout. Otherwise dispatch three reviewers in parallel, one lens each: **correctness**, **contracts**, and **integration**.

Fill in the context header of `reviewer-brief.md` beside the router (intent, out of scope, check results, mechanical commits to skip) and pass it with the commit range or spec path. Do not paste the diff; the reviewer reads the repository. After a review returns, verify the working tree is unchanged, untracked files included, since read-only is an instruction rather than tool enforcement. A reviewer that returns no verdict has not reviewed: read its error output, fix the dispatch or take the next route, and say plainly when no review happened.

## Fix loop

Check every finding: fix it, or decline it with a reason. Any finding without a failing scenario is FYI. Never write a verdict yourself, and do not agree just to end the loop. If review has grown the diff, cut before adding.

Record fixed and declined findings by id (`S1`, `S2`, ...) and the reviewer's verdict in each fix commit message; that commit count is the round count, with no other record. Continue later rounds in the same reviewer session wherever the harness can resume it; otherwise pass a fresh reviewer the findings ledger from the commit messages.

Stop at eight rounds as a hard cap—reaching it is not approval; end the loop and hand the open findings to the person. Escalate any item disputed twice to the person. `MAJOR_RETHINK` stops the loop; `NEEDS_HUMAN` goes to the person.

## Other review routes

Spec reviews and goal final reviews use this same playbook with that kind set in the brief header. For read-only questions like "what could this break" or "is this safe to merge", find and prove the one fact the change is safe because of (or where it fails) and change nothing.
