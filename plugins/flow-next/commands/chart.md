---
name: chart
description: Decision-map discovery for one oversized/unclear idea before capture - ground, chart a frontier, resolve one decision per invocation, brief for capture
argument-hint: "[idea | <chart-id> [--decision <n>] [--status] | <tracker-url>]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-chart`

The ONLY purpose of this command is to call the `flow-next-chart` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles mode detection (chart / work / status / locator re-entry), bounded grounding, prompt-first operation inference, flowctl chart mutations, attended gates, and the terminal `CHART_VERDICT=` line.
