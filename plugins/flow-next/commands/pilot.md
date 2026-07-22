---
description: Single-tick autonomous build-loop conductor (one item, one stage per invocation); --backlog/--auto widens it to triage the whole open backlog
argument-hint: "[--backlog|--auto] [--spec <fn-N>] [--dry-run] [--review=<backend>] [--research=<grep|rp>] [--depth=<level>]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-pilot`

The ONLY purpose of this command is to call the `flow-next-pilot` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles spec selection, stage classification, sub-skill dispatch, advancement verification, and the terminal PILOT_VERDICT line.
