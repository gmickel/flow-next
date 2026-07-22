---
name: land
description: Cadence-tick autonomous PR babysitter (CI-fix, resolve, converge, merge, close, release)
argument-hint: "[--dry-run]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-land`

The ONLY purpose of this command is to call the `flow-next-land` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles PR discovery, the per-PR gate tree (CI tri-state, patience window, review signal), resolve-pr dispatch, the gated merge + post-merge tail (spec close, tracker, release), and the terminal LAND_VERDICT line.
