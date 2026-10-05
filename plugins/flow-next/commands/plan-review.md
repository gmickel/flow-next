---
name: plan-review
description: Carmack-level plan review via Codex, Copilot, Cursor, Claude or a host reviewer
argument-hint: "<fn-N> [--review=codex|copilot|cursor|none] [focus areas]"
disable-model-invocation: true
---

# IMPORTANT: This command MUST invoke the skill `flow-next-plan-review`

The ONLY purpose of this command is to call the `flow-next-plan-review` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles the review logic.
