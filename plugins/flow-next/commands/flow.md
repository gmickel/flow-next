---
name: flow
description: Conductor - an idea or change request, a spec or task id, a tracker issue, a branch or path, a bug report, a how or why question, something slow, a behaviour-keeping cleanup, a design fork, or "what next"; --auto drives a ready spec unattended (--tick for one hop) and ends with a PILOT_VERDICT line
argument-hint: "[<anything>] [--explain] [--review=<backend>] | --auto [<spec-id>] [--tick] [--backlog] [--explain] [--review=<backend>] [--research=<grep|rp>] [--depth=<level>]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-flow`

The ONLY purpose of this command is to call the `flow-next-flow` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill routes from its shared routing reference, dispatches the existing stage skills, re-evaluates after each hop, and stops at the next human decision. `--explain` prints the route and its reason with no `.flow/` write and no dispatch. `--auto` runs the same route unattended from the ready flag, hop after hop to a terminal (`--tick` for exactly one hop), and ends with one `PILOT_VERDICT` line.
