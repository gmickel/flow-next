---
title: Paired-snapshot setter must write both halves atomically (merge base)
date: "2026-06-03"
track: bug
category: data
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-52, tracker-sync, merge-base, 3-way-merge, invariant, setter, impl-review]
problem_type: data
symptoms: set-merge-base partial update pins one half of the 3-way merge base to a stale sync point
root_cause: "per-flag setter updated each merge-base half independently, breaking the paired-snapshot invariant"
resolution_type: fix
related_to: [bug/data/migrationrollback-cli-10-review-cycle-2026-05-08]
---

## Problem
`flowctl sync set-merge-base` (fn-52.1) stored the 3-way merge base as two independent fields (`mergeBaseFlow`/`baseHashFlow` and `mergeBaseTracker`/`baseHashTracker`) and updated each only when its CLI flag was passed. That permitted a PARTIAL write: `--flow` alone refreshed the flow half while leaving the tracker half pinned to an OLDER sync point (or vice versa). The merge base is meant to be a paired snapshot of both bodies at ONE sync point — the common ancestor for the agentic 3-way merge (.4). Mismatched halves would make that merge compare against stale context and surface false conflicts or silently merge wrong.

## Solution
Require both sides together: in `cmd_sync_set_merge_base`, reject the call when exactly one of flow/tracker is supplied (`(flow is None) != (tracker is None)`) and when neither is supplied — error before any state write, so a partial update never lands. Both `--flow/--flow-file` AND `--tracker/--tracker-file` must come together. flowctl.py `cmd_sync_set_merge_base`. Regression test `test_merge_base_partial_update_rejected` asserts flow-only / tracker-only / no-arg all error AND leave prior state unchanged.

## Prevention
When a stored value is a multi-field SNAPSHOT-AT-A-POINT (merge base, paired hash+body, before/after pairs), make the setter write all fields atomically as a unit — never per-flag. An "update only what was passed" setter is correct for independent fields but silently corrupts paired-snapshot invariants. Add a "partial update rejected, state unchanged" regression test for any paired-snapshot writer.
