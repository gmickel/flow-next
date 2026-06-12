---
title: Lavish interactive-only gate must check MODE var AND env markers in-snippet
date: "2026-06-12"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-capture/workflow.md
tags: [fn-62, lavish, skill-authoring, safety-gates, review-feedback, html-artifacts]
problem_type: build-error
symptoms: "RP NEEDS_WORK x2: lavish open/poll reachable in autofix and autonomous runs despite generate-only prose"
root_cause: "Snippet gated on command -v only; then on env markers only — mode:autofix lives in the MODE skill var, not env"
resolution_type: fix
related_to: [bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12, bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
fn-62.3 wired the Lavish session open into capture §5.10 / plan Step 8.5 with the interactive-only contract stated in prose, but the bash snippet opened on `command -v lavish-axi` alone. RP impl-review returned NEEDS_WORK twice: round 1 — no non-interactive guard at all in the snippet; round 2 — env-marker guard added but capture's `mode:autofix` (a skill argument carried in the `MODE` var, not an env var) still wasn't checked mechanically.

## What Didn't Work
Round 1 fix only gated on the env-marker family (FLOW_AUTONOMOUS / FLOW_RALPH / REVIEW_RECEIPT_PATH) plus a comment telling autofix runs to set LAVISH_OK=false themselves — a comment is prose, not enforcement.

## Solution
Commits 1235c6d + fce92a1: `LAVISH_OK` gate inside the snippet with BOTH checks — `[[ "${MODE:-interactive}" != "interactive" ]] && LAVISH_OK=false` (MODE comes from SKILL.md mode-detection) AND the env-marker family check; `lavish-axi` open + the poll instruction both live inside the guarded branch. Codex mirror regenerated.

## Prevention
When a skill's side-effect gate spans two signal kinds (skill-argument mode vars like MODE/AUTONOMOUS and env markers like FLOW_RALPH), the snippet must check BOTH mechanically — a code comment instructing the agent to set a flag is the same prose-only gate the fn-60 lesson (skill-workflow-snippets-must-enforce) already flagged. Trace every mode signal named in the surrounding prose to an actual test in the snippet.
