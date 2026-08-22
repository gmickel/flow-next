---
title: Concurrent gating draws + soft terms falsify a 'frozen' eval pre-registration
date: "2026-08-21"
track: bug
category: build-errors
module: agent-evals/studies/rolling-frontier-2026-08
tags: [fn-203, eval-design, pre-registration, wall-clock, codex-review, review-feedback]
problem_type: build-error
symptoms: "Reviewer: same-second arm launches measure cross-arm interference; discretionary terms + unbounded reruns in a frozen protocol"
root_cause: Speed-motivated concurrency and prose defaults registered as if frozen; verdict-bearing measurements shared a machine
resolution_type: fix
related_to: [bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18, bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12, bug/build-errors/eval-ledger-feature-rows-must-disclaim-2026-07-18, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12, bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/optional-side-effect-snippets-need-2026-06-12, bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27, bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26, bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05, bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
The fn-203 rolling-frontier eval pre-registration froze "all three arms launched same-second on one machine (contention hits all arms equally)" as its batch plan, plus soft terms ("~3x", "with margin", "borderline") and an unbounded batch-rerun path on invalidated draws. Codex review (2 rounds) flagged: (1) same-second concurrency does NOT make contention equal - arms with different concurrency profiles throttle each other asymmetrically, so a concurrent gating draw partially measures cross-arm interference; (2) a "frozen" protocol containing discretionary terms or missing rerun/aggregate bounds lets different operators reach different verdicts from identical results.

## What Didn't Work
Round-1 fix kept batch 1 concurrent and made only the replication batch sequential ("declared limitation"). Rejected: a concurrent batch could still issue a DECISIVE verdict under interference - declaring a confound does not remove it from a verdict-bearing measurement.

## Solution
All gating draws sequential on an otherwise-idle machine: baseline first (enables the live 1.5x kill rule since W0 is known), treatment arms in randomized order; host load recorded per draw. Every soft term replaced with numbers (decisive bands 20%/10%, provisional 100-min task ceiling, 8h/20M per draw); per-arm aggregates frozen (24h/60M -> INCONCLUSIVE terminal); batch reruns bounded (max 2 attempts -> INCONCLUSIVE). Amendments logged in the study changelog as pre-draw amendments. Key unlock: the binding R-ID said "paired same-machine draws" - same-second was only a registered default the task text allowed amending, so complying with review did not contradict the spec.

## Prevention
When pre-registering wall-clock evals: (a) never let a concurrent draw carry a gating verdict - sequential idle-machine execution or mechanically-impossible interference only; (b) grep the frozen protocol for "~", "with margin", "clearly", "borderline" without numeric definitions; (c) every invalidation/rerun path needs a bounded attempt count and an explicit terminal outcome. Check whether a challenged design choice is bound by the R-ID or only by a registered default before declining a review finding.
