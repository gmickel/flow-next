---
title: Optional side-effect snippets need guarded git steps; check-ignore the exact fil
date: "2026-06-12"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-make-pr/workflow.md
tags: [fn-62, make-pr, html-artifacts, skill-authoring, set-e, check-ignore, review-feedback]
problem_type: build-error
symptoms: "RP NEEDS_WORK: unguarded git add/commit under set -e could abort make-pr before gh pr create; dir-level check-ignore misclassified glob-ignored artifacts"
root_cause: Sibling lens snippet copied without re-deriving failure semantics; non-fatal promise lived in prose only; ignore probe targeted the directory not the file
resolution_type: fix
related_to: [bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05, bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08, bug/build-errors/docs-activation-command-for-string-enum-2026-06-05, bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12, bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12, bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11, bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10, bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10, bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
fn-62.4 wired the PR render lens into make-pr (Phase 1.5). RP impl-review returned NEEDS_WORK with two findings on the new snippet: (1) the prose promised "artifact failure is non-fatal" but the stage/commit snippet ran bare `git add` + `git commit` under the skill's `set -e` — a hook rejection, index lock, or nothing-to-commit would abort the whole skill before `gh pr create`, violating the "PR still created, link skipped" acceptance criterion; (2) the link-mode probe was `git check-ignore -q .flow/artifacts/` (directory) — repos ignoring via `.flow/artifacts/**`, `*.html`, or the exact file path don't match the directory probe, so ignored artifacts entered repo/blob-link mode.

## What Didn't Work
Copying the sibling spec-lens snippet shape (capture §5.10 / plan Step 8.5) without re-deriving the failure semantics for make-pr's stricter acceptance: those lenses run last in their skill (failure has nothing downstream to kill), make-pr's lens runs BEFORE the PR creation it must never block.

## Solution
Commit 74a4ecd: `LENS_OK` flag with a fully guarded chain — `git add -- "$ARTIFACT_PATH"` → `git diff --cached --quiet -- "$ARTIFACT_PATH"` (byte-identical regeneration → no empty commit, blob link already resolves) → pathspec `git commit ... -- "$ARTIFACT_PATH"`; any failure flips `LENS_OK=false`, clears `LINK_MODE`, emits exactly one stderr note, and the run proceeds. Ignore probe now targets the exact artifact file.

## Prevention
Two checks when adding an optional side-effect block to a skill that has hard downstream invariants: (a) every git/external command inside an "advisory" feature must be failure-guarded in the snippet itself — "best-effort" in prose plus unguarded commands under `set -e` is the same prose-only-gate drift as fn-60/fn-62.3; (b) `git check-ignore` probes the EXACT file you will link/commit, never its parent directory — `**`, extension globs, and exact-path rules don't mark the directory as ignored.
