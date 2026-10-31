# Review, QA, and completion-review selection

## Live QA

`pipeline.qa` is a string enum `off | on | auto`; any other value is `off`.

- `off`: QA runs only when the user invokes `/flow-next:qa`.
- `on`: QA runs at all-tasks-done, before make-pr, on every spec.
- `auto`: QA runs at all-tasks-done when the spec's acceptance describes UI behaviour on a drivable surface **and** a target can be started (a documented start command, a deploy URL, or `.flow/features/`). Otherwise the stage records `skipped(config: pipeline.qa=auto: <no UI-observable criteria | no drivable surface | no startable target>)` and the route advances.

`auto` only: read [qa-auto.md](qa-auto.md) to decide both halves and record the line.

QA never hard-blocks the loop; `NEEDS_WORK` and `BLOCKED` advance to make-pr, and their findings become open items on a draft PR.

Attended, QA leaves its verdict uncommitted; on a spec branch (not the default branch), commit only
the receipt QA wrote and its `.history` directory with `chore(flow): qa verdict <spec-id>`, the
subject the freshness check peels. Under `--auto`, QA commits it itself.

## Review, completion review and receipts

Implementation, design and completion review are run and recorded by the stages that own them
(work, plan-review) before flow reaches all-tasks-done. Their selection rules and the receipt
line are in [gate-selection-more.md](gate-selection-more.md); read it only when a route
skips the stage that owns one of them, or to write a stage line SKILL.md's report shape does
not cover.
