---
title: Who-wins ladder must check the collision case before single-field rules
date: "2026-06-03"
track: bug
category: runtime-errors
module: plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md
tags: [fn-52, tracker-sync, who-wins, status, deadlock, conflictTiebreak, ordering, impl-review]
problem_type: runtime-error
symptoms: tracker=done × flow=in-progress auto-closed the spec; conflictTiebreak deadlock fallback was unreachable
root_cause: terminal-wins branch ordered before the deadlock branch in the if/elif who-wins ladder; the collision pair matched the earlier rule and resolved silently
resolution_type: fix
---

## Problem
fn-52.5's status who-wins reconcile loop (status-sync.md) documented a "status deadlock → conflictTiebreak" fallback, but the loop evaluated the `tracker ∈ {done,verified}` terminal-wins branch BEFORE the deadlock branch. A `tracker=done × flow=in-progress` collision satisfies BOTH the terminal-wins and in-progress-wins single-field rules, so the first matching branch (terminal-wins) silently auto-closed the spec — the deadlock fallback was unreachable, contradicting the file's own deadlock section, Fixture S-E, and the R7 acceptance criterion. Surfaced by impl-review (rp), Major/confidence 100.

## What Didn't Work
First attempt at the fix introduced a base-aware guard (`flowMoved`/`trackerMoved` against a stored `baseStatus`). That invented a flowctl field that does not exist — flowctl's sync state persists the merge-base BODY + content hashes only, never a prior STATUS. The guard would have read a null/undefined field.

## Solution
Move the deadlock check to FIRST position in the reconcile loop (before terminal-wins and in-progress-wins). The terminal-vs-active pair itself (`tracker∈{done,verified} && flow==in-progress`, plus the mirror) IS the deadlock signal — it needs no stored prior status, reading only the two current normalized statuses (always available). Residual terminal/in-progress branches then fire only when there is no live-work collision. Fixtures updated: S-A reset to flow=planned (clean tracker-wins-terminal), S-E kept flow=in-progress (the deadlock the first-position check catches). status-sync.md reconcile loop + deadlock section.

## Prevention
When a policy table has multiple single-field rules that a single input can satisfy simultaneously (here: a status pair matching both terminal-wins and in-progress-wins), the COLLISION case must be checked FIRST, or whichever rule is ordered earlier silently wins and the documented fallback becomes dead code. For an if/elif ladder encoding a who-wins policy: list the "both rules match → escalate" branches above the individual winning rules. Also: before adding a guard that reads stored state, confirm the field is actually persisted (grep flowctl for the schema) rather than assuming a "base X" snapshot exists for every dimension.
