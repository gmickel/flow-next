---
name: visual
description: Restate a spec, task, diff, or the current topic as a compact markdown visual digest
argument-hint: "[spec id | task id | git range | free-form topic]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-visual`

The ONLY purpose of this command is to call the `flow-next-visual` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill handles target detection (spec / task / diff / ad-hoc), state reads, shape selection, and the digest. It is read-only — chat output only.
