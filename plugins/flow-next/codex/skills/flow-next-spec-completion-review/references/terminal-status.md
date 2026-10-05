# Host terminal status (gated reference)

> Read from workflow-common.md only when `BACKEND` is `host`.

## Capped round

- host continues to SKILL.md's Step 0.5 checkpoint immediately; it confirms
  the recorded `needs_work` (repairing a write that did not land), then emits
  `ESCALATE:` and exits 4. Do not attempt another reserve/dispatch first.

## Record the terminal verdict

For host, `review-rounds record --status-target completion` is the one
status owner (with a journaled receipt, the status lands when `attach`
publishes it). Execute the SKILL.md Step 0.5 checkpoint again now: it repairs
a write that did not land and emits the terminal only after persistence
succeeds. Codex/copilot/cursor/claude handlers already self-write status; their next
invocation also runs Step 0.5 first, so a handler-side write failure recovers
without another reviewer dispatch.

For host, status persists once on every delivered terminal path and
Step 0.5 emits the matching terminal — SHIP → `ship` (exit 0),
capped-NEEDS_WORK → `needs_work` (exit 4), and
NEEDS_HUMAN → `needs_human` (exit 4, `ESCALATE: reviewer requested human
review`). A delivered NEEDS_HUMAN is terminal at ANY round: never reserve or
dispatch another review for it. The write happens immediately after the
final verdict is recorded and before `ESCALATE:` / exit 4; no later control
flow is assumed. Transport failure, malformed verdict, and retry outcomes are
non-terminal and never write completion status.
