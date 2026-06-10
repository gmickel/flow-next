---
title: R2 ask-block must never anchor in autonomous hard-error prose; mode-rename sweep
date: "2026-06-10"
track: bug
category: build-errors
module: "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-make-pr/workflow.md"
tags: [fn-59, sync-codex, codex-mirror, R2-injection, is_negative_context, autonomous, FLOW_AUTONOMOUS, make-pr, review-feedback]
problem_type: build-error
symptoms: Mirror instructs Codex to ask the user inside the RALPH/AUTONOMOUS hard-error branch of make-pr
root_cause: Descriptive parenthetical naming the ask tool in an autonomous bullet matched ACTIVE_ASK_VERBS; no negative-context rule for hard-error/no-user prose
resolution_type: fix
related_to: [bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
fn-59.3's regenerated Codex mirror injected the R2 plain-text numbered-prompt INSTRUCTION block directly under make-pr's `When RALPH=1 or AUTONOMOUS=1:` branch (codex/skills/flow-next-make-pr/workflow.md:43) — instructing Codex to ASK the user inside the branch whose very next bullet says Phase 0 questions hard-error. RP impl-review flagged it P1: in autonomous/pilot mode this could make make-pr prompt/hang instead of erroring deterministically. Root cause: the canonical bullet carried a descriptive parenthetical "(Interactive resolves the same via `AskUserQuestion`; ...)" — after tool-rewrite, "via `plain-text numbered prompt`" matched ACTIVE_ASK_VERBS, and none of the `is_negative_context` patterns covered hard-error/no-user prose, so the once-per-file injector anchored there (it is the FIRST positive match in the file).

## What Didn't Work
Relying on the existing negative-context patterns (Never use / cannot call / skips / no ... call / It is not). A contrast-parenthetical that POSITIVELY names the ask tool while describing the interactive branch from inside an autonomous-context bullet slips every one of them. The post-sync token audit also passed — tokens were all rewritten; the bug was placement semantics, not surviving tokens.

## Solution
Two-sided fix (commit 2550f95):
1. Reworded the canonical bullet to drop the tool name entirely — "(Interactive mode resolves the same gaps with its usual Phase 0 info prompts — not a confirm gate.)" (plugins/flow-next/skills/flow-next-make-pr/workflow.md:40). The tool reference was not load-bearing there; SKILL.md:27 + workflow.md:1279 carry it.
2. Hardened scripts/sync-codex.sh `is_negative_context`: lines containing 'hard-error' or 'no user to ask' alongside the prompt phrase are now negative contexts — descriptive refuse-to-ask prose can never anchor the R2 block again.
A second stale-wording sweep also surfaced: make-pr phases.md + workflow.md still said Ralph-only ("Open tasks + Ralph -> exit 2", "Ralph forces draft", "Ralph alone hard-errors") where the implemented behavior is RALPH || AUTONOMOUS — updated to Ralph/autonomous everywhere except the deliberately Ralph-only PR_URL stdout line.

## Prevention
- Never NAME the ask tool inside a bullet that describes an autonomous/Ralph/hard-error branch — even parenthetically. The injector anchors on the LINE; a positive "via <tool>" in refuse-to-ask prose flips the mirror's meaning. Describe interactive behavior without the tool name, or move it to the interactive section.
- When a skill gains a second no-questions mode (e.g. AUTONOMOUS alongside RALPH), grep ALL its files for the old mode name (`grep -n "Ralph" phases.md workflow.md`) — checklist/Done-when lines drift independently of the implementing code blocks (three stale spots survived two prior reviews).
- After regen, for each changed mirror file check WHERE the R2 block landed (`grep -n "Ask the user via plain text"`) and read the surrounding branch — placement inside a `RALPH/AUTONOMOUS` conditional is always wrong.
