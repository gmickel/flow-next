---
name: flow-next:epic-review
description: "[deprecated] Renamed to /flow-next:spec-completion-review — invokes the new skill"
argument-hint: "<fn-N> [--review=rp|codex|copilot|cursor|none]"
---

# `/flow-next:epic-review` is renamed to `/flow-next:spec-completion-review`

This slash command was renamed in flow-next 1.0.0 as part of the epic→spec vocabulary alignment. It still works as a thin redirect; the alias is removed in 2.0.0.

Invoke the `flow-next-spec-completion-review` skill now and forward `$ARGUMENTS` to it. Do not run the review yourself; the skill handles backend dispatch and the fix loop.
