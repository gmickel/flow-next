# Unattended

An unattended run (`--auto`) never asks. Consent is the invocation naming the item, the tracker's ready state when configured, or, with no tracker, a spec waiting in `.flow/specs/open/` on the default branch: take the first ready one in dependency order (`waiting.md`). With nothing ready, stop as `NO_WORK`, naming anything blocked by a loop or an unknown id. A spec in `.flow/specs/parked/` is started only when the invocation names it or its issue, and the report says it was parked; otherwise never start, move, or ask about it. When an issue picked up only because it was ready leads to a parked spec, a person is needed: say so on the issue with how to start it.

Build, review as much as `review.md` decides for this change, and open the PR without confirmation. A change `review.md` leaves unreviewed is unreviewed here too, and the PR says so and why. Land it only when the invocation asked for through merge and a person authorised it. When asked for one step per invocation, run the next stage once and stop.

When, before starting, the spec already has work on a remote branch (one that has moved it out of `open/`, or is named for it) that this checkout does not hold (no local branch at or ahead of it), and no open pull request, another run is building it. Do not start it and do not build on that branch, whatever else says to stay on a branch already doing the work: with the spec or its issue named, stop as `NO_WORK` and name the branch; with no item named, take the next ready spec. Look at the remote once more before review, where most of the cost is; if such a branch has appeared by then, stop as `NO_WORK`, name it, and start nothing else. Never force a push the remote rejects: stop as `NEEDS_HUMAN` and name both commits.

When a person is needed, post why on the issue or PR, move the item out of the tracker's ready state at once, and stop. On a transient failure, change nothing and end as `BLOCKED` so retrying is safe; keep no attempt counter.

Name any worktree the run created in the final report.

## Terminal line

End with exactly one fixed line parsed by outside tools:

`PILOT_VERDICT=<CODE> spec=<id> stage=<stage> reason="<one line>"`

Stages are `spec`, `build`, `review`, `pr`, and `land`; use `-` for `spec` or `stage` when none applies. Include `pr=<number>` in `reason` once a PR exists, and `merged=<sha>` after a merge.

- `ADVANCED`: finished a stage; more work remains.
- `NO_WORK`: nothing eligible to run.
- `DEFERRED_TO_LAND`: the PR is ready to merge, waiting on merge consent or the caller.
- `BLOCKED`: a transient failure stopped the run; nothing changed.
- `ASKED`: posted closing questions on an issue that missed the bar and moved it out of ready.
- `NEEDS_HUMAN`: stopped for a person on any other decision or failure after posting and un-readying the item.
- `GOAL_MET`: all criteria of a goal spec are met.
