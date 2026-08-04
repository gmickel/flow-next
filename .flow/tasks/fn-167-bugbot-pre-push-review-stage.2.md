---
satisfies: [R2, R3, R4, R5, R6, R7, R8]
---
# fn-167-bugbot-pre-push-review-stage.2 Implement the prepush-review pilot stage

## Description
Implement the stage exactly as specced. Starts only after task 1 returns a go.

### Scope

- **Config**: `pipeline.prepushReview`, strict scalar string enum `on|off`, default `off`. Non-enum values (`true`, `null`, typo) resolve to off, never to on and never to an error. Read from the tick's existing root config snapshot via jq; never add a second `config get` call (fn-110 invariant).
- **Skill**: new `flow-next-prepush-review` (SKILL.md + workflow.md), following existing skill conventions. Single-purpose: invoke `/review-bugbot` host-natively, read findings, write receipt. No backend split, no `--review=` passthrough, no model pins, no prompt authoring, no `flowctl cursor` wrapper, no `cursor-agent -p`.
- **Pilot**: add `prepush-review` to the stage enum and the permitted dispatch set. Classify it at the all-tasks-done juncture, after `qa` when `pipeline.qa == on`, before `make-pr`. Dispatch only when the gate is on AND the Cursor host driver is active; otherwise clean skip, never an error, never `NEEDS_HUMAN`. Autonomy-safe: every outcome advances, the stage never asks a question.
- **Receipt**: `prepush_review` shape per the spec's API Contracts, including `patch_id`, `head_sha`, `findings`, and `findings_visible_on_pr` (value set from task 1's result).
- **make-pr**: assert `HEAD` unchanged since the receipt's `head_sha`; on mismatch emit a warning in the output, never a failed tick and never a blocked push.
- **PR body**: carry findings into the cognitive-aid PR body ONLY if task 1 showed they do not surface natively on the PR. Zero findings produces no section rather than an empty one.

### Non-goal, load-bearing

No fix loop. Advisory only. An unbounded fix loop on a per-review-priced reviewer rebuilds the 3.3x churn multiplier this feature exists to remove, inside flow-next. If a loop is ever added it is hard-bounded on the land bounded-fix-budget precedent, never loop-until-SHIP. Record the non-goal in code comments where a future contributor would reach for the loop.

### Tests

- Gate off (and each non-enum value) leaves pilot's dispatched stage set and `PILOT_VERDICT` output byte-for-byte unchanged.
- Gate on + Cursor host: stage dispatched exactly once, in position, both with `pipeline.qa` on and off.
- Gate on + non-Cursor host: clean skip.
- Bugbot unavailable / unauthed / rate-limited: `BLOCKED` receipt, tick still advances.
- HEAD mismatch: warning emitted, push proceeds.

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
