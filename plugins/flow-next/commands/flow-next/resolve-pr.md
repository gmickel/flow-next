---
name: flow-next:resolve-pr
description: Resolve PR review feedback — fetch unresolved threads, triage, dispatch resolver agents, reply + resolve via GraphQL.
argument-hint: "[PR number | comment URL | blank for current branch's PR] [--dry-run] [--no-cluster]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-resolve-pr`

The ONLY purpose of this command is to call the `flow-next-resolve-pr` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles fetch, triage, dispatch, validate, commit, reply, and resolve.
