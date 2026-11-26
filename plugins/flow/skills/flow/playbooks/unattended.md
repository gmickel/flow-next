# Unattended

An unattended run (`--auto`) never asks. Consent is the invocation naming the item, or the tracker's ready state when configured; with neither, stop as `NO_WORK`.

Build, review as much as `review.md` decides for this change, and open the PR without confirmation. A change `review.md` leaves unreviewed is unreviewed here too, and the PR says so and why. Land it only when the invocation asked for through merge and a person authorised it. When asked for one step per invocation, run the next stage once and stop.

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
