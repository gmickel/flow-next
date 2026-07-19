---
title: Glob-walk file loads need lstat screen + RecursionError; revalidate TTL post-sta
date: "2026-07-19"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [gate, green-receipt, fail-closed, fifo, json]
problem_type: runtime-error
symptoms: FIFO candidate hangs gate check; nested JSON aborts walk; slow git status honors stale receipt
root_cause: open() before file-type screen; RecursionError outside except tuple; TTL verdict cached pre-status
resolution_type: fix
related_to: [bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27]
---

## Problem
The fn-116 ancestor-walk added glob-driven receipt scanning (`gate check` candidate walk + `gate receipt` prune-on-write). Review found two introduced defects: (1) opening glob matches without screening file type first - `open()` on a FIFO blocks forever, and deeply nested JSON raises `RecursionError`, which the `(OSError, json.JSONDecodeError, ValueError)` except tuple does NOT catch - violating the skip-never-abort contract; (2) the exact-receipt refactor computed the TTL age BEFORE the `git status` cleanliness check and cached the verdict, so a slow status could honor a receipt that aged past 24h mid-check (ordering equivalence with the pre-refactor path broken).

## What Didn't Work
Reusing the naive `path.open()` + `json.load` pattern per glob match (duplicated in scan and prune), and caching `_gate_receipt_valid`'s result across the status call to avoid a second validation.

## Solution
One bounded loader `_gate_load_receipt_file` (flowctl.py ~27611): `lstat` + `stat.S_ISREG` screens FIFOs/symlinks/sockets BEFORE any open, 64KiB size cap, `RecursionError` added to the except tuple; shared by candidate scan and prune. Exact path re-runs `_gate_receipt_valid` AFTER cleanliness so TTL uses the post-status clock (early schema/HEAD/fingerprint rejects stay pre-status for order equivalence). Regressions: git-shim that sleeps on `status` with a 24h-minus-1.5s receipt; FIFO/oversized/nested-JSON candidates.

## Prevention
When a loop opens files discovered by glob in a skip-never-abort walk, always lstat-screen for regular files and bound the read; remember `RecursionError` escapes JSON except tuples. When refactoring terminate-style inline checks into a cached pure validator, re-evaluate time-dependent predicates at the ORIGINAL evaluation point, not capture-time.
