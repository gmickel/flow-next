---
name: flow
description: Conductor - an idea or change request, a spec or task id, a tracker issue, a branch or path, a bug report, a how or why question, something slow, a behaviour-keeping cleanup, a design fork, or "what next"; --auto drives a ready spec unattended (--tick for one hop) and ends with a PILOT_VERDICT line; --until=merge continues through scoped gated landing
argument-hint: "[<anything>] [--until=merge] [--explain] [--review=<backend>] | --auto [<spec-id>] [--until=merge] [--tick] [--backlog] [--explain] [--review=<backend>] [--depth=<level>]"
disable-model-invocation: true
---

# IMPORTANT: This command MUST invoke the skill `flow-next-flow`

The ONLY purpose of this command is to call the `flow-next-flow` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill owns routing, `--explain`, `--auto` (`--tick`, `--backlog`, `--goal`, `--from-issue`), and `--until=merge` landing authority.
