---
name: features
description: Seed or maintain the committed user-POV feature map at `.flow/features/`
argument-hint: "[--init]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-features`

The ONLY purpose of this command is to call the `flow-next-features` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill verbatim. The skill handles autonomy refusal, state-resolved mode detection (seed when `.flow/features/` is absent or `--init` is passed; maintain when the map is present), seed/maintain execution, and the terminal `FEATURES_VERDICT=` line.
