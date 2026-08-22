---
title: "Concurrent-loop skill prose: linear checklist + non-blocking claims contradict"
date: "2026-08-22"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md
tags: [fn-203, work-rolling, scheduler, event-driven, plan-sync-barrier, codex-review, review-feedback]
problem_type: build-error
symptoms: Rolling scheduler admitted only after each task's full review tail; SHIP branch bypassed the plan-sync serial barrier
root_cause: Event loop written as linear per-return checklist; prose claimed non-blocking behavior the control flow did not implement
resolution_type: fix
related_to: [bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18, bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27, bug/build-errors/concurrent-gating-draws-soft-terms-2026-08-21, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12, bug/build-errors/eval-ledger-feature-rows-must-disclaim-2026-07-18, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12, bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/optional-side-effect-snippets-need-2026-06-12, bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27, bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26, bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05, bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
The fn-203.4 beta scheduler reference (rolling-frontier work variant) shipped its Phase-3 loop as "handle all of 3d (integrate + review + fix loop + done), then recompute admission" - which silently serializes admission behind each task's review tail, defeating the rolling-frontier design the skill exists for. A second round caught the mirror image: the SHIP completion branch routed straight back to admission (3a), bypassing the 3e plan-sync barrier, so with planSync.enabled=true a next task could be claimed and anchored before the completed task's plan-sync ran.

## What Didn't Work
Writing an event-loop as a linear per-return checklist and asserting non-blocking behavior in prose ("a NEEDS_WORK fix loop never blocks admission of others") without restructuring the control flow to make it true. The claims and the described flow contradicted each other; a cross-family reviewer read the flow, not the claims.

## Solution
Restructure the scheduler as an explicit event-driven lifecycle (rolling-scheduler.md 3d): two event kinds (worker-return / review-completion), review LAUNCHED concurrently via thin-wrapper subagent at worker return, admission recomputed after EACH event, slot held from admission to done-or-escalation, and the SHIP branch routing through 3e (done(N) -> plan-sync(N) -> any anchor) BEFORE freeing the slot. Degraded inline-review path named and reported rather than implied.

## Prevention
When skill prose describes a concurrent loop, write the state machine (events, states, slot accounting, barrier ordering) rather than a linear checklist plus non-blocking claims - and check every completion path against every fail-closed gate (plan-sync serial barrier) the skill inherits. A prose assertion that contradicts the described control flow is a P1, and cross-family review reliably finds it.
