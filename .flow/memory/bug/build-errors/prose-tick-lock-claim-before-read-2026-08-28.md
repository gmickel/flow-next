---
title: "Prose tick lock: claim before read, serialized reap, liveness refresh, persisted"
date: "2026-08-28"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-land/workflow.md
tags: [fn-208, land, concurrency, ledger, skill-prose, codex-review, review-feedback]
problem_type: build-error
symptoms: "One review round found 4 defects in a freshly written prose lock: read-before-claim, reaper race, unreachable dependency, evidence-free comparison"
root_cause: Lock written as an afterthought after the state it protects; comparisons asserted without persisting the prior observation
resolution_type: fix
---

## Problem
A prose-level tick lock added to the land conductor (fn-208.1) drew four review findings in one round: the ledger snapshot was read before the claim was taken (stale-snapshot gating), age-only stale clearing could evict a live long tick and let two reapers race rmdir/mkdir, a new triage rule depended on a read the surrounding prose said was unreachable ("Only green proceeds"), and a "same failure text" comparison had no recorded evidence to compare against.

## What Didn't Work
Writing the claim as an afterthought paragraph placed after the state it protects, and asserting comparisons ("same check, same failure text") without persisting the earlier observation.

## Solution
Take the claim before the first ledger read (the read moved inside the claimed interval); serialize stale takeover behind a second atomic reaper claim with an in-claim age re-check; refresh claim mtime at every phase boundary, per-PR loop iteration, and before each bounded blocking call so the stale window measures crash, never work; make the red-CI path through the thread read explicit where neighboring prose said only green proceeds; and record a `flake_sig` (check name + first failure line) in the ledger at rerun time so the repeat-failure comparison has evidence. All in `plugins/flow-next/skills/flow-next-land/workflow.md` Phase 0/2.4/3.1.

## Prevention
When adding a lock to prose (or code): the claim precedes every read of the state it protects; any stale-takeover path needs its own serialization plus an in-claim re-check; any timeout-based staleness needs a liveness refresh sized to the longest legitimate operation; and any "matches the previous X" rule needs the previous X persisted at observation time.
