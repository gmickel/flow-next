---
name: guide
description: Prompt-first router that recommends the smallest sufficient flow-next workflow for the current starting state
argument-hint: "[situation description]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-guide`

The ONLY purpose of this command is to call the `flow-next-guide` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill is stateless routing only - matrix match, optional one blocking question, natural-language next prompt. No artifacts, no flowctl mutation, no pipeline stage.
