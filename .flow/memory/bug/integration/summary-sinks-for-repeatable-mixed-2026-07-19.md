---
title: "Summary sinks for repeatable mixed-outcome events need per-event lines, not one "
date: "2026-07-19"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-work/phases.md
tags: [prose-contract, summary-template, gate-diet, fn-102, review-finding]
problem_type: integration
symptoms: "single Gates: enum slot let later host gate outcomes overwrite earlier skips (silent-skip risk)"
root_cause: copied a one-of-N terminal-slot pattern (Tracker sync:) for an event stream that can mix outcomes per run
resolution_type: fix
---

## Problem
fn-102.2 wired host-layer gate skips into the /flow-next:work Phase 5 final-summary template as a single `Gates: <enum>` slot. Codex impl-review flagged (Major) that Phase 4 can run periodically and produce MIXED outcomes in one run (some gates receipt-reused, some run full, a later pass docs-only) - a singular enum slot lets later outcomes overwrite earlier skips, violating the spec's zero-silent-skip contract (R3). A second Minor: docs-only GATE_SKIPPED evidence lines shipped without the human clause R3 requires alongside the machine-parseable prefix.

## What Didn't Work
Modeling the summary sink as one mandatory template field with exactly-one-of-N states (copied from the `Tracker sync:` slot pattern) - correct for a single terminal audit, wrong for an event stream.

## Solution
phases.md: accumulate every Phase 4 skip/honor outcome (gate_id + receipt sha8) and emit ONE `Gates:` line per outcome in the Phase 5 summary (template annotated "one line per outcome; repeat for each"). worker.md: `GATE_SKIPPED:<gate>:docs-only - cumulative diff classified tier-B (no executable paths touched)`. Commit 28f5c0bb.

## Prevention
When adding a summary/receipt sink for events that can occur multiple times with mixed values in one run, model it as accumulated per-event lines, not a single enum slot. Reserve one-of-N slots for terminal single-shot audits (like `Tracker sync:`). Check "can this fire more than once per run?" before copying an existing slot pattern.
