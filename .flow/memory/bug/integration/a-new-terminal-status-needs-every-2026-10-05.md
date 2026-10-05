---
title: "A new terminal status needs every reader of done swept, tracker included"
date: "2026-10-05"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [fn-282, retire, task-status, tracker-sync, closed-in-range, status-policy]
problem_type: integration
symptoms: Retired spec projected as completed; reopened retired spec skipped completion review; renamed retired spec read as a new close
root_cause: Readers inferred delivery from status done or required every task to be exactly done
resolution_type: fix
last_updated: "2026-10-05"
last_audited: "2026-10-05"
---

## Problem
fn-282 added a second terminal state: a retired spec keeps `status: done` plus a `retired` record, and its never-run tasks read `retired`. Review found three readers that still treated `done` as the only end state. Tracker sync projected a merged retired spec as completed. `next` routed completion review only when every task was exactly `done`, so a retired spec that was reopened and finished never got reviewed. The closed-in-range filter dropped the deleted path of a renamed spec, so renaming an already-retired spec counted as a new close.

## What Didn't Work
Sweeping only the `== "done"` comparisons in flowctl.py. That covered close, ready, start, block, validate and the export counts. It missed readers that see a done spec and infer "delivered" (the tracker policy in flowctl_tracker/status/policy.py), and a cheap-path filter that narrowed the spec path list before the base-identity read.

## Solution
One settled set, `TASK_SETTLED_STATUSES = {"done", "retired"}`, used by every reader that asks whether a task is still work, including `next`'s all-tasks check. `flow_to_normalized` returns `cancelled` for a merged retired spec, which `decide` already defers. `specs_closed_in_range` keeps every changed spec path for the base read and only early-returns when no record-only change is a retirement.

## Prevention
When a change adds a terminal value or a sibling of `done`, grep for readers of the parent field as well as for the literal: `status == "done"`, `all(... == "done")`, jq `select(.status != "done")` in shell scripts, and the tracker package's own projection of spec status. Never filter a path list before an identity comparison that needs deleted paths. In the tracker policy, every value `flow_to_normalized` can return needs a matching branch in `decide` (flowctl_tracker/status/policy.py), or the new rung is mapped but never written; keep probe outcomes an exhaustive enum, including `ambiguous` and `probe-error`, never folded into `none` or `merged`.
