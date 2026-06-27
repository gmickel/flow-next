---
title: "flowctl on-disk per-key counter: count by stored key + lock + coerce sort"
date: "2026-06-27"
track: bug
category: runtime-errors
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-68, pilot-log, tick-counter, race-condition, flock, rp-review, review-feedback]
problem_type: runtime-error
symptoms: duplicate/colliding tick values; summary crashes with str-vs-int TypeError on a non-int tick
root_cause: tick counted by filename slug not stored id; glob-count+write race; sort key used 'value or 0' instead of int() coercion
resolution_type: fix
---

## Problem
A flowctl decision-log subcommand (`pilot-log append`/`summary`, fn-68.1) that
writes per-id-monotonic `tick` rows under `.flow/pilot-runs/` shipped three
review-surfaced defects in the tick/summary path:
1. `tick` was counted by a filename-slug glob, so two distinct opaque ids that
   normalize to the same safe-filename slug (`"a/b"` vs `"a-b"`) shared one
   counter.
2. `summary` sorted on `r.get("tick") or 0` — a corrupt/hand-edited row with a
   non-int tick (`"x"`) survived the `or` and raised a str-vs-int `TypeError`,
   crashing the entire read.
3. After fixing (1) by counting stored `id == raw_id`, the count+write was still
   race-prone: two concurrent same-id appends both read N rows and both wrote
   `tick=N+1` (duplicate tick).

## What Didn't Work
Per-slug glob count (assumes slug ≡ id). `value or 0` as a numeric fallback
(only catches None/empty, not a non-empty non-int string). A content-hash in the
filename alone (prevents path clobber, not duplicate ticks — same id → same hash).

## Solution
- Count by reading each candidate row's stored `id` and matching `== raw_id`
  (slug glob is only a cheap pre-filter). flowctl.py `cmd_pilot_log_append`.
- Coerce the sort key via `int(...)` with a 0 fallback (`try/except
  (TypeError, ValueError)`); keep the emitted tick verbatim (facts-only).
- Serialize count+write under a per-id exclusive `flock` (reuse the existing
  `_flock`/`LOCK_EX` cross-platform helper; no-op on Windows). Lock file is a
  dot-prefixed `.pilot-<idhash>.lock` sibling so neither the count glob
  (`pilot-<slug>-*.json`) nor the summary glob (`pilot-*.json`) ever sees it.

## Prevention
For any "monotonic per-key counter" derived from files on disk: (a) key the
count on the STORED key, never the filename slug; (b) serialize count+write
under a per-key lock — a glob-count + separate write is a classic
read-modify-write race; (c) numeric sort keys over external/hand-editable JSON
must coerce defensively (`int()` in try/except), never `value or 0`. Regression
tests should include an actual concurrent (subprocess) append to exercise the
OS-level flock, not just in-process threads.
