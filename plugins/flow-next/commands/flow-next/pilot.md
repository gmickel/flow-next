---
name: flow-next:pilot
description: Single-tick autonomous build-loop conductor (one ready spec, one stage per invocation)
argument-hint: "[--spec <fn-N>] [--dry-run] [--review=<backend>] [--research=<grep|rp>] [--depth=<level>]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-pilot`

The ONLY purpose of this command is to call the `flow-next-pilot` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles spec selection, stage classification, sub-skill dispatch, advancement verification, and the terminal PILOT_VERDICT line.
