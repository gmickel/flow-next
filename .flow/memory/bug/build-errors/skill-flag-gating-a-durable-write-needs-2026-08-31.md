---
title: "Skill flag gating a durable write needs exact-token parse, not substring"
date: "2026-08-31"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-capture/SKILL.md
tags: [fn-214, skill-bash, argument-parsing, capture, codex-review, review-feedback]
problem_type: build-error
symptoms: --no-planning / --no-plan=false set NO_PLAN_OPT=1 (durable no_plan write consent)
root_cause: Substring flag match copied from adjacent benign flags into a durable-state gate
resolution_type: fix
related_to: [bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18, bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27, bug/build-errors/canonical-3c-edits-vanish-from-codex-2026-08-28, bug/build-errors/concurrent-gating-draws-soft-terms-2026-08-21, bug/build-errors/concurrent-loop-skill-prose-linear-2026-08-22, bug/build-errors/delegating-cli-wrapper-inherits-2026-08-30, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12, bug/build-errors/eval-ledger-feature-rows-must-disclaim-2026-07-18, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12, bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/optional-side-effect-snippets-need-2026-06-12, bug/build-errors/prose-tick-lock-claim-before-read-2026-08-28, bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27, bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26, bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05, bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
Capture's new `--no-plan` flag (fn-214 R5) was parsed with the same substring idiom as the file's other flags (`[[ "$RAW_ARGS" == *"--no-plan"* ]]`). Codex review reproduced `--no-planning` and `--no-plan=false` setting `NO_PLAN_OPT=1` — lookalike tokens became consent for durable spec state, violating the never-inferred contract.

## What Didn't Work
Copying the adjacent flag parses. Substring matching is tolerable for flags whose false positive is benign, but this flag writes durable state (`flowctl spec set-no-plan`), so a lookalike is a silent wrong write.

## Solution
Exact-token loop (plugins/flow-next/skills/flow-next-capture/SKILL.md, Mode Detection): iterate `for TOK in $RAW_ARGS`, compare `[ "$TOK" = "--no-plan" ]`, rebuild the remainder without the matched token. Same word-split idiom as pilot's parser, so host-shell behavior is consistent. Verified under bash: lookalikes rejected, exact token detected and stripped.

## Prevention
When a skill flag gates a durable write (state field, file, config), parse it as an exact standalone token, never a substring — and test the lookalike inputs (`--flag-suffix`, `--flag=value`) in the same breath. Substring stays acceptable only for flags whose misparse is inert.
