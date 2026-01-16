---
name: flow-next:sync
description: Manually trigger plan-sync to update downstream task specs after implementation drift
argument-hint: "<id> [--dry-run]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-sync`

The ONLY purpose of this command is to call the `flow-next-sync` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles the sync logic.
