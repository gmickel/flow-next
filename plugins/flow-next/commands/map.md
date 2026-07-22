---
description: Wrap `clawpatch map` for a semantic feature index of the repo (~20 languages, provider-free by default)
argument-hint: "[--source <heuristic|auto|agent>] [-- <extra clawpatch args>]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-map`

The ONLY purpose of this command is to call the `flow-next-map` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles install detection, version-range guard, `clawpatch init` (when `.clawpatch/` absent), the `.clawpatch/.gitignore` skeleton, the provider-free `clawpatch map --source heuristic` default invocation, and the result summary.
