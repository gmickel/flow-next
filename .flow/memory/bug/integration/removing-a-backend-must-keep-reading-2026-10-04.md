---
title: Removing a backend must keep reading the state it already wrote
date: "2026-10-04"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [review-backend, removal, legacy-receipts, fn-280]
problem_type: integration
symptoms: "rp removal dropped a legacy recovery receipt gate, reset QA findings lineage, fell through to other reviewers, hid the notice"
root_cause: deleted rp branches and a mode rename treated persisted rp-era state as dead code
resolution_type: fix
---

## Problem
Removing the `rp` review backend (fn-280) was mostly deletion, but three review draws found that deleting the backend also deleted guarantees attached to data it had already written. A persisted `rp` completion attempt lost its receipt check on terminal recovery and could promote `completion_review_status` to `ship` without the receipt. Renaming the QA receipt-driven mode from `rp` to `receipt` made the next QA receipt start a fresh findings lineage, because lineage is scoped by mode. A stale `rp` value was treated as unset and fell through to a lower-precedence backend, and the tracker's configured-review predicate still counted it as configured. Plan's preflight call discarded stderr, so the removal notice never reached the user.

## What Didn't Work
Treating a stale value as "unset" (the lenient parser returning None) and deleting every `backend == "rp"` branch as dead code. Both looked like plain removal, but each one changed behaviour for state already on disk.

## Solution
- A removed value stops precedence and resolves to `ASK` (`_is_removed_backend_value` in `resolve_review_spec` and `cmd_review_backend`). The tracker's `_backend_off` adds `rp` and `export`.
- The legacy `rp` clause in completion terminal recovery stays, with a comment.
- `_read_legacy_receipt_mode` maps a QA receipt's `rp` mode (and its findings backend) to `receipt` at the two lineage loaders.
- Plan's preflight no longer uses `2>/dev/null`.

## Prevention
When removing a backend, mode or enum value, grep for every persisted record that can carry it (attempt rows, receipts, findings containers, tracker predicates) and decide whether to keep reading each one. Delete only the dispatch paths. Every rename of a stored scope key needs a test that reads an old record and then writes the next generation. Check every skill call that sends stderr to `/dev/null` when a CLI starts reporting on stderr.
