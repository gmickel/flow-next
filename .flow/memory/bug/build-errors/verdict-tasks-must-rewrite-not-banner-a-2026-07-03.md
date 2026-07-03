---
title: "Verdict tasks must rewrite, not banner, a sibling task's flipped scope"
date: "2026-07-03"
track: bug
category: build-errors
module: .flow/tasks
tags: [fn-83, plan-sync-gate, task-marking, verdict, workflow]
problem_type: build-error
symptoms: Sibling task carried FAIL-verdict banner + contradictory gate-wiring body; worker could wire the failed gate
root_cause: Banner-only marking leaves the original Approach/Acceptance executable below the note
resolution_type: fix
---

## Problem
fn-83.6 rendered a FAIL ship-gate verdict that changed a sibling task's (fn-83.4) scope from "wire the gate" to "ship without gate wiring". The first marking approach prepended a verdict banner to fn-83.4's Description but left the original body below it — Approach still said "phases.md 3e gate branch (mode matrix + audit sampling)", and Acceptance still demanded the gate wiring. RP impl-review flagged it (Major, confidence 100): a future worker re-anchoring on that task can follow the lower instructions and wire the failed feature.

## What Didn't Work
Banner-only marking. A contradiction between a banner and the body is not resolved in the banner's favor by an agent executing the task — workers execute Approach/Acceptance, and prose that survives below a "this is now out of scope" note remains executable instructions.

## Solution
Rewrote fn-83.4's whole body to the FAIL branch: Approach states spawn semantics UNCHANGED (no probe invocation, no mode matrix, no audit), Acceptance items assert the ABSENCE of gate wiring ("zero references to plan-sync-probe/gate/ledger/audit in the skill layer"), `satisfies` updated ([R5,R7,R10] → [R5,R6,R10]; R7 lapses with the gate). Commit c5829fd3.

## Prevention
When a verdict/decision task flips a sibling task's scope, REWRITE the sibling's Approach + Acceptance to the surviving branch — never just banner it. Acceptance items should assert the absence of the dropped behavior so a worker cannot re-introduce it and still pass.
