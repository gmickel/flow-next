---
title: Retiring an upserted record needs a reopen on recurrence (upsert keeps stale)
date: "2026-09-26"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-features/references/feature-entry-contract.md
tags: [feature-map, memory-upsert, lifecycle]
problem_type: integration
symptoms: Recurring feature-map drift after retirement stayed stale and uncounted
root_cause: memory upsert updates a stale match in place without reactivating it
resolution_type: fix
---

## Problem
fn-262 added drift-note retirement (`memory mark-stale` when a route is re-proven) to the feature map. Readers file drift notes through `memory upsert` on a deterministic title. Upsert matches stale entries and updates them in place without changing status, so a route that drifted again after retirement stayed stale and vanished from every open-drift count (`features status`, maintain's default `memory list`).

## What Didn't Work
Adding retirement alone. The existing find-or-create was correct in isolation; the new lifecycle step made its "status unchanged on update" semantics a silent hole.

## Solution
The reader contract (feature-entry-contract.md "Writers and drift notes", QA §5.5 fence) follows an `"action": "updated"` upsert with `memory mark-fresh <entry_id>`. The test in test_features_status.py covers report -> retire -> report again -> maintain recommended.

## Prevention
When adding a close/retire step to a record that another path finds-or-creates by identity, test the full cycle: create -> close -> recur. Also check that any rollback of the close step cannot touch pre-existing uncommitted edits on the same file (maintain now skips retiring a dirty note).
