---
title: "Multi-writer record precedence: pipeline order is not chronology"
date: "2026-09-27"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-features/references/feature-entry-contract.md
tags: [feature-map, resolved-feature, carrier, repair-loop]
problem_type: integration
symptoms: older QA record outranked newer task evidence; worker re-copied stale spec line
root_cause: precedence assumed stages run once in order; verbatim copy of upstream value
resolution_type: fix
---

## Problem
fn-263 made `resolved_feature` a record every live-app stage reads and writes (spec line, task done evidence, QA receipt). The first draft picked the "newest" record by assumed pipeline order (QA receipt first), and the worker still copied the spec line verbatim. Repair loops (work after QA, or a task re-resolving) broke both: an older QA record outranked newer task evidence, and a later task could re-copy the stale spec value and become "last task with a record" again.

## What Didn't Work
Ordering carriers by the nominal stage order (flow -> work -> QA). Stages re-run; order is not chronology.

## Solution
- Contract step 2 (`flow-next-features/references/feature-entry-contract.md`, "Live-app stages"): the QA receipt's record counts only while no code commit follows its `head_sha` (the same freshness notion make-pr uses); otherwise the last task record, then the spec line.
- worker.md Phase 5: record the value the task's live drive actually used; copy the spec line only when no earlier task carries a record.
- Reuse skips selection, not the index; re-resolve when the file is gone, drops the sub-feature, or has a new Last proven line.

## Prevention
For any multi-writer carrier, walk a repair loop (A -> B re-resolved -> later reader/writer) before shipping the precedence rule, and never let a downstream writer copy an upstream value verbatim when a newer one may exist.
