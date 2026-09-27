---
title: Honest unmet-outcome promise needs a path through review's coverage gate
date: "2026-09-27"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-work/references/hill-climb.md
tags: [hill-climb, review, coverage-gate, flow-auto]
problem_type: integration
symptoms: Budget-exhausted hill climb promised a draft PR but review would block it
root_cause: Unmet target R-ID had no verdict-compatible status; review gate and auto handoff not traced
resolution_type: fix
related_to: [bug/integration/drop-receipt-to-break-codex-2026-05-09]
---

## Problem
The hill-climb reference said a run that spends its budget short of the target "still completes honestly" with the target reported unverified and a draft PR under `flow --auto`. Review (all three fan-out draws) found no path to that draft PR: worker Phase 4 needs SHIP, the reviewer judges the parent spec's target R-ID, and an escalation stops `flow --auto` before make-pr.

## What Didn't Work
Telling the worker to record the outcome in the task description and "answer" a target finding from the record. It gave the reviewer no verdict-compatible way to accept the unmet criterion.

## Solution
Use the review prompt's existing coverage semantics: only a non-deferred `not-addressed` R-ID forces NEEDS_WORK. The worker writes the outcome into the task description (which the reviewer reads) stating the target's R-ID is `deferred` (not met within the pre-registered budget; the gap is carried to the PR). The SHIP rule accepts R-IDs `met` or `deferred`, so a SHIP on the kept commits carries the task through done and make-pr with the target shown unverified (plugins/flow-next/skills/flow-next-work/references/hill-climb.md, section 6).

## Prevention
When a route promises an honest "completed but not met" outcome, trace it through every downstream gate (worker review, coverage gate, done, autonomous make-pr) before writing the promise; name the existing status that carries it rather than inventing a new one, and check it against the verdict rule itself, not only the hard gate (`partial` passes the coverage gate but not SHIP's "all R-IDs met or deferred"; `deferred` passes both).
