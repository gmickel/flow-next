---
title: Backlog SELECT must not drop a dep-blocked item to NO_WORK — it routes to BLOCKE
date: "2026-06-27"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-pilot/references/backlog-mode.md
tags: [fn-68, pilot, backlog-mode, skill-authoring, select-vs-triage, terminal-grammar, rp-review, review-feedback]
problem_type: build-error
symptoms: "A backlog tick with only ready-but-dep-blocked work wrongly terminates NO_WORK instead of BLOCKED, losing the dep-wait signal"
root_cause: "SELECT (Phase 1f) excluded dep-blocked items from selection, but TRIAGE (Phase 2) resolves dep-unsatisfied to a state-changing BLOCKED terminal; the SELECT exclusion set was wider than it should be"
resolution_type: fix
related_to: [bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12, bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12, bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/optional-side-effect-snippets-need-2026-06-12, bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/status-policy-map-needs-a-matching-2026-06-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
In `references/backlog-mode.md` (fn-68 pilot backlog mode), Phase 1f SELECT lumped a signalled-but-**dep-unsatisfied** candidate into the same fall-through bucket as unsignalled / parked items — "if every signalled one is parked / dep-blocked → NO_WORK / DEFERRED_TO_LAND". But Phase 2's triage table routes `dep-unsatisfied → BLOCKED`. So a backlog tick whose only ready work was dep-blocked would wrongly terminate as `NO_WORK`, silently losing the dep-wait signal instead of surfacing it.

## What Didn't Work
Treating "selectable" as "immediately advanceable". A dep-blocked item is still SELECTABLE — it gets picked and routed to a state-changing `BLOCKED` terminal (R10: a live triage never ends on a no-op). Only a `status=open` parked question (already surfaced, waiting on a human) legitimately removes a candidate from the selection pool.

## Solution
Phase 1f now states a signalled item is selectable EVEN when a dep is unsatisfied; it routes to Phase 2 `BLOCKED <id> by <dep>` (surfaces the dep wait). `NO_WORK` is reserved for a genuinely empty pool (no signalled, unparked candidate at all); `DEFERRED_TO_LAND` unchanged. The Phase 2 `dep-unsatisfied` row was tightened to `BLOCKED <id> by <dep>` as a state-changing terminal (circular/unsatisfiable dep → `ASKED` instead). backlog-mode.md Phase 1f + Phase 2 table.

## Prevention
When a skill workflow defines a SELECT phase plus a downstream TRIAGE/CLASSIFY phase, cross-check the SELECT exclusion set against every terminal the TRIAGE phase can emit: an item the triage phase can resolve to a state-changing terminal (BLOCKED/ASKED) must NOT be in SELECT's "drop to NO_WORK" bucket. The terminal-grammar contract (here R10: every live triage resolves to a state-changing terminal) is the invariant to grep against.
