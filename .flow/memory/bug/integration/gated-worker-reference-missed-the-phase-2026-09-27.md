---
title: Gated worker reference missed the Phase 1b bridged path; per-task proof cells hi
date: "2026-09-27"
track: bug
category: integration
module: plugins/flow-next/agents/worker.md
tags: [worker, bridge, gated-reference, pr-aid]
problem_type: integration
symptoms: Bridged child never sees a reference pointed to only from Phase 1.5; per-task proof cells exceed 16
root_cause: Pointer placed only on the standard path; cell count scaled with task count
resolution_type: fix
---

## Problem
fn-264 added a gated worker reference (defect-route.md) with its only pointer in worker Phase 1.5. Phase 1b's bridged path skips Phase 1.5 and hands the child only a pointer prompt, so a bridged implementer would have committed a fix without ever seeing the reference. Separately, a per-task set of five PR proof cells overflowed the briefing's 16-cell cap at four defect tasks.

## Solution
Name the gated reference in Phase 1b's pointer list (item 1, as a file to read, next to the Resolved via Research section) and add it to the On-return range check. Make PR proof cells shared per briefing, summarizing several tasks, instead of per task.

## Prevention
When adding a worker-side gated reference, check both implementation paths (standard Phase 1.5/2 and the Phase 1b bridge pointer prompt). When adding per-task PR briefing cells, multiply by task count against the 16-cell proof cap.
