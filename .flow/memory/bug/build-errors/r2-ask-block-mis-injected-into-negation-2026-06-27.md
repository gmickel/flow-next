---
title: R2 ask-block mis-injected into negation-only autonomy prose on mirror regen
date: "2026-06-27"
track: bug
category: build-errors
module: "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-pilot, plugins/flow-next/skills/flow-next-tracker-sync/steps.md"
tags: [fn-68, sync-codex, codex-mirror, pilot, backlog-mode, tracker-sync, AskUserQuestion, R2-injection, is_negative_context, autonomy, review-feedback]
problem_type: build-error
symptoms: "RP impl-review NEEDS_WORK: the R2 'Ask the user via plain text' instruction block injected into pilot's Forbidden/Phase-3.5 negation prose AND before tracker-sync's Phase-0 autonomy invariant (contradicts R14 never-prompt)"
root_cause: is_negative_context() in sync-codex.sh did not catch the negation shapes of autonomous-only prose (forbidden/never-reached); the first fix was case-sensitive lowercase and missed the uppercase 'NO code path may reach' invariant
resolution_type: fix
related_to: [bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27, bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03, bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12, bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/optional-side-effect-snippets-need-2026-06-12, bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18, bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10, bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/status-policy-map-needs-a-matching-2026-06-18, bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
fn-68.5 regenerated the Codex mirror for pilot backlog mode + tracker-sync. The
sync-codex.sh R2 injector adds an "Ask the user via plain text. Render the
options ..." INSTRUCTION block once per file at the first active-ask anchor. It
mis-injected the block into NEGATION-ONLY autonomy prose in TWO places:
1. The pilot mirror (Forbidden section + Phase-3.5 async-valve heading) — pilot
   ONLY negates AskUserQuestion ("never reached", "is forbidden", "never an
   interactive", "Never asks interactively"); it never asks.
2. The tracker-sync mirror, directly BEFORE the Phase-0 autonomy invariant
   ("Under RALPH=1 NO code path may reach ...") — caught by RP impl-review, not
   the first local audit.
Both contradict R14 (under FLOW_AUTONOMOUS/mode:autonomous the path NEVER prompts).

## What Didn't Work
- A first-pass local mirror audit + the existing sync validators (askq_refs,
  request_user_input) passed clean — they are TOKEN scans; they do not detect a
  structurally-misplaced R2 INSTRUCTION block. (Same blind spot as fn-53.5's
  mid-sentence injection.)
- The first is_negative_context() fix used a case-SENSITIVE lowercase
  "no (?:code )?path reaches" — it missed the tracker-sync invariant's uppercase
  "NO code path may reach" (uppercase + "may reach" modal), so RP caught a second
  instance the pilot-only fix didn't cover.

## Solution
- scripts/sync-codex.sh is_negative_context(): added a CASE-INSENSITIVE clause
  covering the (no|never) + (code )?path + reach(es|ed|able)? family with an
  optional modal ("may"/"can"/...), plus "is/are forbidden", "never an
  interactive", "never asks interactively". Verified it does NOT over-match
  genuine ask sites (interview/prospect) — the R2-block file set for the 24
  genuinely-asking skills is unchanged. The tracker-sync R2 block now lands at
  the GENUINE Phase-1 discovery ASK (where the human IS prompted), after the
  Phase-0 invariant.
- Also: breadcrumb stripper regex `(?:\*\*)?Codex mirror` (optional opening bold)
  so a bold-led "**Codex mirror is regenerated in fn-68.5**" breadcrumb strips
  like the bare-led tracker-sync one. Reshaped the canonical backlog-mode.md
  bullet to lead with "Codex mirror".
- New test test_pilot_backlog_mirror_safety.py asserts NO R2 block in the pilot
  mirror AND no R2 block before the tracker-sync Phase-0 invariant (both proven
  to FAIL when the defect is reintroduced).

## Prevention
- The R2 injector's negative-context heuristic must be CASE-INSENSITIVE and
  cover the full reach-family + modal. Any autonomous-only skill (negation-only
  AskUserQuestion prose) is an injection HAZARD — when regenerating its mirror,
  grep the mirror for "Render the options below as a" and confirm it lands at a
  GENUINE ask site, never before an autonomy/forbidden invariant.
- Lock it with a contract test (R2 block absent from negation-only files; never
  precedes the Phase-0 invariant). A token-scan validator is NOT enough — assert
  STRUCTURAL placement.
