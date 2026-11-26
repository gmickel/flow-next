# Review

## Dispatch

Send review to another model family through `orchestrate.md`. If a named reviewer cannot be reached, stop and say so; never substitute a reviewer silently. When no preference is stated and no other family is reachable, the same family reviews and that fact goes on the PR's review line. A reviewer from the builder's own vendor, the builder's own model included, is a same-family review wherever its name appeared; never report it as another family.

Decide whether a change is reviewed by its risk, not its size. Review every change that touches persisted or shared state, concurrency, security, data layout or migrations, and every multi-file feature. A small local fix to output, wording or display is not reviewed: say so and why. A spec or instruction that asks for review is followed whatever the size.

When a review runs, the first round uses one reviewer for a small change in one area that touches none of those, and three in parallel otherwise, one lens each: **correctness**, **contracts**, and **integration**.

Fill in the context header of `reviewer-brief.md` beside the router (intent, what the request says must stay as it is in the person's own words, out of scope, check results, mechanical commits to skip) and pass it with the commit range or spec path. Do not paste the diff; the reviewer reads the repository. After a review returns, verify the working tree is unchanged, untracked files included, since read-only is an instruction rather than tool enforcement. A reviewer that returns no verdict has not reviewed: read its error output, fix the dispatch or take the next route, and say plainly when no review happened.

## Findings

Fix a finding only when it shows the change does the wrong thing in a scenario the request covers. Hardening, extra shutdown or error paths, wider refactors, style, and problems that were there before the change are follow-ups: list them in the hand-off as plain facts, and do not offer to fold them in. When a finding points at machinery the change added that nobody asked for, remove it; if review has grown the diff, cut before adding. Any finding without a failing scenario is FYI. Decline a finding with a reason. Never write a verdict yourself, and do not agree just to end the loop.

Record fixed and declined findings by id (`S1`, `S2`, ...) and the reviewer's verdict in each fix commit message; that commit count is the round count, with no other record.

## Rounds

When a person is waiting, hand the result back first, in its own message, then run the review in the background and report its verdict, and any fix, when it lands. Where the host cannot wake the session when the review finishes, wait for it instead. After fixing, re-review once, with one reviewer, in the same reviewer session wherever the harness can resume it, and stop there: give the person any findings that remain, with the reviewer's reasons. Later fixes, including ones the person asks for, get focused tests, not another review. A PR waits for the verdict.

Unattended, or when asked to review until SHIP, loop. Each later round is one reviewer, under the later-round rule in `reviewer-brief.md`. Where a session cannot be resumed, pass a fresh reviewer the findings ledger from the commit messages. Stop at eight rounds as a hard cap—reaching it is not approval; end the loop and hand the open findings to the person. Escalate any item disputed twice to the person. `MAJOR_RETHINK` stops the loop; `NEEDS_HUMAN` goes to the person.

## Other review routes

Spec reviews and goal final reviews use this same playbook with that kind set in the brief header. For read-only questions like "what could this break" or "is this safe to merge", find and prove the one fact the change is safe because of (or where it fails) and change nothing.
