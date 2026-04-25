---
name: flow-next:memory-migrate
description: Migrate legacy `.flow/memory/{pitfalls,conventions,decisions}.md` flat files into the categorized YAML schema — host agent classifies each entry directly
argument-hint: "[mode:autofix] [optional scope hint — e.g. pitfalls.md]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-memory-migrate`

The ONLY purpose of this command is to call the `flow-next-memory-migrate` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill handles mode detection (`mode:autofix` token), legacy-file detection, per-entry classification, categorized writes, verification, and optional cleanup.
