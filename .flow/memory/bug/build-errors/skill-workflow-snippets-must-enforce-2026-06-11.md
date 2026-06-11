---
title: "Skill workflow snippets must enforce what the prose mandates (vars, gates, dispa"
date: "2026-06-11"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-land/workflow.md
tags: [fn-60, land, skill-authoring, codex-review, safety-gates, review-feedback]
problem_type: build-error
symptoms: "Codex NEEDS_WORK: PR_NUMBER unset at use, echo-only safety gate falls through to tail, tracker dispatch was a :-placeholder"
root_cause: Workflow bash written as illustrative pseudo-code while binding behavior lived only in surrounding prose
resolution_type: fix
related_to: [bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18, bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10, bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26, bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05, bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
fn-60.1 authored the new flow-next-land skill (cadence PR babysitter). Codex impl-review returned NEEDS_WORK with three findings, all "skill prose vs executable snippet" drift:
1. Discovery used `gh pr view "$PR_NUMBER"` before any branch of the outcome table assigned `PR_NUMBER` (open-PR path needed `OPEN_PRS[0].number`, re-entry path needed `MERGED_PR_NUM`) — a mechanical run would fail or reuse a stale loop value.
2. The post-merge safety gate (`git merge-base --is-ancestor`) only `echo`-ed on failure and fell through to the tail, while the surrounding prose mandated NEEDS_HUMAN + skip-the-tail — the snippet undermined the gate the prose promised.
3. The opt-in tracker touchpoint body was a `:` no-op with comments (copied from make-pr §5.6's illustrative shape), but the acceptance required an actual dispatch — easy for an executing agent to skip.

## What Didn't Work
Treating workflow bash blocks as illustrative pseudo-code when the surrounding prose carries the binding behavior. An executing agent (and a reviewer) reads the SNIPPET as authoritative; prose-only safety gates and placeholder dispatch blocks don't survive review.

## Solution
Commit 85c582e: (1) assign `PR_NUMBER` explicitly inside each discovery outcome branch before the authorship check; (2) hard `TAIL_OK` branch — ancestor-check failure skips the ENTIRE tail with NEEDS_HUMAN; (3) replaced the `:` placeholder with a mandatory "dispatch via the Skill tool" instruction block naming the operation + event tag.

## Prevention
When authoring a new skill workflow: for every bash snippet, (a) trace each `$VAR` to an assignment in the same or an earlier phase INCLUDING per-loop-iteration freshness, (b) any safety gate the prose mandates must be a hard branch in the snippet (set a flag, skip the protected steps), never an `echo` + fall-through, (c) a mandatory side-effect (skill dispatch, receipt) must be an explicit instruction block — a `:` no-op placeholder is only acceptable for genuinely optional illustrative hooks.
