---
name: flow
description: Attended conductor - takes any starting point, picks the smallest sufficient route, runs it, and stops at the next human decision; --explain prints the route without running it
argument-hint: "[<anything>] [--explain] [--review=<backend>]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-flow`

The ONLY purpose of this command is to call the `flow-next-flow` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill routes from its shared routing reference, dispatches the existing stage skills, re-evaluates after each hop, and stops at the next human decision. `--explain` prints the route and its reason with no `.flow/` write and no dispatch.
