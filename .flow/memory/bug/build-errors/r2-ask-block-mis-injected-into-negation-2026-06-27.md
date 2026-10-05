---
title: R2 ask-block mis-injected into negation-only autonomy prose on mirror regen
date: "2026-06-27"
track: bug
category: build-errors
module: "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-flow/auto.md, plugins/flow-next/skills/flow-next-tracker-sync/steps.md"
tags: [fn-68, sync-codex, codex-mirror, flow-auto, backlog-mode, tracker-sync, AskUserQuestion, R2-injection, is_negative_context, autonomy, review-feedback]
problem_type: build-error
symptoms: "RP impl-review NEEDS_WORK: the R2 'Ask the user via plain text' instruction block injected into the unattended driver's Forbidden/async-valve negation prose AND before tracker-sync's Phase-0 autonomy invariant (contradicts never-prompt)"
root_cause: is_negative_context() in sync-codex.sh did not catch the negation shapes of autonomous-only prose (forbidden/never-reached); the first fix was case-sensitive lowercase and missed the uppercase 'NO code path may reach' invariant
resolution_type: fix
last_updated: "2026-10-05"
last_audited: "2026-10-05"
related_to: [bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18]
audit_consolidates: [bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10, bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05]
---

## Problem
Regenerating the Codex mirror for the unattended driver's backlog mode (then the pilot skill, now `flow --auto` in `skills/flow-next-flow/auto.md`) and for tracker-sync, the sync-codex.sh R2 injector put its "Ask the user via plain text. Render the options ..." instruction block into negation-only autonomy prose in two places:
1. The driver's Forbidden list and async-valve heading. The driver only negates the ask tool ("never reached", "is forbidden", "never asks interactively"); it never asks.
2. The tracker-sync mirror, directly before its Phase-0 autonomy invariant ("NO code path may reach ..." on an unattended run).
Both told an unattended run to stop and wait for a user, contradicting the never-prompt rule.

## What Didn't Work
- The existing sync validators (`AskUserQuestion` and `request_user_input` token scans) passed. A token scan cannot see a structurally misplaced instruction block.
- The first `is_negative_context()` fix matched a lowercase "no (code )path reaches" only, and missed the uppercase "NO code path may reach" invariant.

## Solution
`is_negative_context()` in scripts/sync-codex.sh gained a case-insensitive clause for the (no|never) + (code )?path + reach(es|ed|able)? family with an optional modal, plus "is/are forbidden", "never an interactive" and "never asks interactively". The tracker-sync block moved to its genuine discovery ask, after the Phase-0 invariant.

## Prevention
- A file with negation-only ask prose (the unattended driver, an autonomy invariant) is an injection hazard. After regenerating its mirror, grep the mirror for `Render the options below as a` and confirm each hit sits at a genuine ask site, never before an autonomy or forbidden rule.
- Placement is structural, so a token scan cannot catch it. Pin it with a test that asserts the block is absent from negation-only files.
- Never name the ask tool in refuse-to-ask prose, even in parentheses. The phrase "blocking question" is rewritten to the same prompt wording and anchors the block too, so keep it out of that prose as well. Describe the interactive behaviour without either, or move it to the interactive section.
- Keep every live ask ("ask the user via `AskUserQuestion`") on one physical line: the block is inserted before the anchor line, not the sentence. Avoid the article "an `AskUserQuestion`", which becomes "an `plain-text numbered prompt`".
- When a skill gains a second no-questions mode, grep all its files for the old mode name; checklist and Done-when lines drift separately from the code blocks.

Consolidated 2026-07-25 from `r2-ask-block-must-never-anchor-in-2026-06-10` and `codex-mirror-audit-must-verify-r2-block-2026-06-05` (same defect class, same function).
