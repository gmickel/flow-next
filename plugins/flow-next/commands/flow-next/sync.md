---
name: flow-next:sync
description: Sync user-level Ralph scripts from plugin with diff backup
---

# IMPORTANT: This command MUST invoke the skill `flow-next-sync`

The ONLY purpose of this command is to call the `flow-next-sync` skill. You MUST use that skill now.

Updates `~/.config/flow-next/ralph/` scripts from plugin templates. Creates backups of local modifications before updating.
