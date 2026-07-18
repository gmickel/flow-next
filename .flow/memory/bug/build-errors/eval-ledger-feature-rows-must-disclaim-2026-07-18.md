---
title: Eval-ledger feature rows must disclaim the optimization ratchet + reconcile deno
date: "2026-07-18"
track: bug
category: build-errors
module: optimization/interview
tags: [fn-100, eval-ledger, ratchet, denominator-reconciliation, codex-review, review-feedback]
problem_type: build-error
symptoms: shipped row violates the ledger's committed keep-ratchet; 11/11 partition claim vs 14 recorded emissions
root_cause: spec-appendix numbers copied into the ledger without reconciling against the ledger's own audit contract and internal counts
resolution_type: fix
related_to: [bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18, bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27, bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12, bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/optional-side-effect-snippets-need-2026-06-12, bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27, bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10, bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26, bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05, bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09, bug/build-errors/unit-rename-substitution-broke-trigger-2026-07-18]
---

## Problem
Recording a FEATURE change (fn-100 frontier rounds) as a row in an optimization-eval ledger (optimization/interview/results.tsv + changelog.md) tripped two Major review findings: (1) the ledger header declares a keep-ratchet (accuracy >= baseline AND (accuracy-up OR tokens-down OR quality-up)) that the feature row silently violated (tokens up, accuracy/quality flat) while carrying status=shipped; (2) an aggregate claim ("11/11 rounds runs, zero violations") did not reconcile with the row's own runs count (14 total emissions), leaving 3 runs unaccounted.

## What Didn't Work
Faithfully copying the spec appendix numbers into the entry without reconciling them against the ledger's own committed audit contract and against each other.

## Solution
(1) Added an explicit "Ledger-contract note" in the Experiment 3 entry + a FEATURE-VALIDATION disclaimer in the tsv description: the optimization keep-ratchet is not claimed; the ship gate is named (accuracy floor + quality >= baseline + partition clean) and the token cost recorded as accepted feature cost (optimization/interview/changelog.md "Ledger-contract note"). (2) Disclosed the exact partition-scored population (11 = 8 v1 + 3 v2 I1; 3 v2 guard reps unscored; 14 emissions total) at all three claim sites (changelog.md, results.tsv, CHANGELOG.md).

## Prevention
When a ledger/results file carries a committed audit rule in its header, any appended row that does not satisfy the rule must name its own exception explicitly - never rely on status wording. Before committing, cross-check every aggregate claim (N/N) against the row's own counts; a reviewer will diff the denominators.
