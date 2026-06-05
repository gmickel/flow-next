---
name: flow-next:qa
description: Live-app real-user QA pass derived from the spec
argument-hint: "<fn-N>"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-qa`

The ONLY purpose of this command is to call the `flow-next-qa` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles spec resolution, scenario derivation from the spec, driving the live app via flow-next-drive, finding-filing, and the verdict.
