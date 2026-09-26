---
name: land
description: Resolve and squash merge one named, currently authorized pull request
argument-hint: "<PR> [--dry-run]"
disable-model-invocation: true
---

# IMPORTANT: This command MUST invoke the skill `flow-next-land`

The ONLY purpose of this command is to call the `flow-next-land` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the named pull request and current session authorization to the skill.
It resolves feedback and CI, checks the specs at the PR head, and merges when
ready and authorized. It prints one terminal LAND_VERDICT line.
