---
title: "Dispatch settings must reach the bridged implementer, not its native wrapper"
date: "2026-10-17"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [judge, tier, effort, bridge, dispatch]
problem_type: integration
symptoms: Tier line claims an effort the bridged implementer never received
root_cause: effort routed to native spawn; routing-block bridge resolved later in the worker
resolution_type: fix
related_to: [bug/integration/a-new-terminal-status-needs-every-2026-10-05, bug/integration/bundled-snapshot-pr-listing-truncation-2026-09-26, bug/integration/review-backend-adapters-move-2026-10-05]
---

## Problem
A dispatch setting computed by the conductor (worker reasoning effort) was routed to the native worker spawn whenever no explicit implementer was passed. When the project routing block named a bridged implementer, worker Phase 1b launched the bridge without that setting, so the native wrapper ran at the chosen effort and the real implementer did not, while the Tier line claimed it was applied. A role-pinned effort also short-circuited the bridged case and dropped the requested effort.

## What Didn't Work
Deciding "bridged" only from the conductor's own inputs (explicit model or mechanical fast model): the routing-block implementer is resolved later, inside the worker, and the conductor never passes it to the judge.

## Solution
A role pin applies only to the native spawn (`if role_effort and not bridged` in `judge_tier_effort`, flowctl.py); bridged implementers carry the effort in `<model> at <effort>`. worker-bridge.md takes the effort from IMPLEMENTER, else the routing block, else the level the TIER_LINE applied.

## Prevention
For any per-dispatch setting, trace it to the process that actually does the work on every reach path (native spawn, explicit bridge, routing-block bridge resolved by the worker), and add a test case per path that asserts where the value lands.
