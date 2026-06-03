---
name: flow-next:tracker-sync
description: Project a flow spec to a tracker (Linear/GitHub) and reconcile body/status/comments two-way — projection, not coordination. NOT plan-sync (/flow-next:sync).
argument-hint: "[discover|push|pull|reconcile|link|unlink] [<id>]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-tracker-sync`

The ONLY purpose of this command is to call the `flow-next-tracker-sync` skill. You MUST use that skill now.

This is **distinct from `/flow-next:sync`** (= plan-sync, the `flow-next-sync` skill, which updates downstream task specs after implementation drift). `/flow-next:tracker-sync` bridges a spec to an external tracker issue. Do not conflate them.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles the discovery ceremony, link/create/unlink ceremony, and the push/pull/reconcile orchestration.
