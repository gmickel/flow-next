# Issue Start

Use this playbook for an unattended start from a tracker issue: the issue named with `--from-issue`, or, with none named and a tracker linked, the first ready issue. Run tracker calls through `edge` (see `tracker.md` for verbs). Starting a goal from an issue and picking by dependency order among ready issues are not supported.

Confirm the issue is in the ready state, which grants consent; with none ready, stop as `NO_WORK` per `unattended.md`. If a linked spec already exists, continue it under `unattended.md`. Otherwise read the issue and its comments.

## The bar

An issue meets the bar when it fits one cohesive PR in an accepted kind—spec-like change, defect, cleanup, performance fix, or hill climb stating a metric and target—and every criterion is testable and traceable to the issue, leaving no open product or design decision to invent. Any stricter bar in `CLAUDE.md` or `AGENTS.md` wins.

## Outcome

If it misses the bar (including non-build requests or goals), build nothing: post the closing questions on the issue, move it out of the ready state at once, and end as `NEEDS_HUMAN` per `unattended.md`.

If it meets the bar, write one linked spec via `spec.md`—or make a direct change with the issue as the request when small and local—and continue under `unattended.md`.
