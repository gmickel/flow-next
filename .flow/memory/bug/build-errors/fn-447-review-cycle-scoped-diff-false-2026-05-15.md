---
title: "fn-44.7 review cycle: scoped diff false-positives + prose-form scaffold drift + "
date: "2026-05-15"
track: bug
category: build-errors
module: "CLAUDE.md, plugins/flow-next/skills/flow-next-plan/steps.md, scripts/sync-codex.sh"
tags: [fn-44, impl-review, codex-review, r21-drift, codex-mirror, scoped-diff, relative-paths]
problem_type: build-error
symptoms: "NEEDS_WORK passes on a docs task: 'missing-from-diff' for files satisfied on branch tip + prose-form scaffold duplication slipping past R21 + broken relative path in regenerated codex mirror"
root_cause: Scoped review with --base <commit> only sees diffs since BASE_COMMIT; commit-message explanations of pre-BASE state don't satisfy the reviewer. R21 drift guard scopes to ^## header co-occurrence and misses prose enumeration. Mirror lives one directory deeper than canonical so any '../../foo' link from a skill resolves wrong in the mirror.
resolution_type: fix
related_to: [bug/build-errors/agent-rename-epic-id-prompt-key-changes-2026-05-08, bug/build-errors/codex-impl-review-false-positive-on-2026-05-09, bug/build-errors/fn-441-review-cycle-json-contracts-html-2026-05-15, bug/build-errors/fn-442-review-both-pass-policy-2026-05-15, bug/build-errors/fn-445-review-r17-enforcement-beyond-2026-05-15, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem
Three rounds of impl-review NEEDS_WORK on a docs/release task before SHIP. The pattern: reviewer flagged "missing file" findings that pointed at work done in *prior tasks* of the same spec (CLAUDE.md by T1, plugin README by T6) but predating BASE_COMMIT for the current task's scoped review. Plus a real R21-shaped drift hazard the existing guard didn't catch (prose enumeration of canonical sections in CLAUDE.md + plan/steps.md), plus a Codex mirror relative-path bug that only manifests in the regenerated mirror.

## What Didn't Work
Pass 1 — Tried to *explain away* the CLAUDE.md / plugin README findings in the fix commit message ("already in place from T1/T6 pre-BASE"). Reviewer can only see the embedded diff for the current task; commit-message prose doesn't satisfy a "missing from diff" finding even when the file already contains the required content on branch tip.

Pass 2 — Re-touched both files in the diff so the reviewer could see them. That worked for the missing-from-diff problem but introduced a *new* finding: my "pull into diff" CLAUDE.md edit *also* enumerated the seven canonical sections inline (prose form, not `## ` headers) — a drift hazard the R21 guard correctly doesn't flag (it scopes to `^## ` co-occurrence within 30 lines) but a careful human reviewer rightly does. Same drift in plan/steps.md.

## Solution
Pass 3 fixes:
1. CLAUDE.md L120 + plan/steps.md L231 — replace prose section enumeration with one-sentence pointer ("section list ... lives there"). Never duplicate the template's section list — even in prose, even in commentary.
2. CLAUDE.md L118 — fix stale "heredoc shown below" wording; pass-2 had changed the example to file redirection but left the introducer text stale.
3. scripts/sync-codex.sh — add sed rewrite `(\.\./\.\./templates/spec\.md) → (../../../templates/spec.md)` to the plan_steps mirror block (line 285). The canonical path at `plugins/flow-next/skills/flow-next-plan/steps.md` correctly uses `../../templates/spec.md`; the codex mirror at `plugins/flow-next/codex/skills/flow-next-plan/steps.md` is one level deeper, needs `../../../`.

## Prevention
- **Scoped-review false-positives recipe**: when a `--base <commit>` review flags "missing from diff" for a file that already contains the required content on branch tip, the fix is to surface the file in the current diff (real edit, ideally a value-add — e.g., a 1.1.0 highlight bullet in the plugin README, or tightening the pointer prose in CLAUDE.md). Explaining via commit message does not work — the next reviewer iteration won't see the explanation.
- **R21 drift guard scope**: the existing guard fires on `^## ` headers co-occurring within 30 lines. Prose enumeration `(Goal & Context, Architecture & Data Models, API Contracts, ...)` slips past. Consider whether the guard should also detect prose enumeration of ≥3 canonical section names within one paragraph — adds value at low false-positive cost.
- **Codex-mirror relative-path debt**: any new canonical-skill link to a path *outside* `plugins/flow-next/skills/` will break in the codex mirror unless sync-codex.sh sed-rewrites it. The mirror lives one directory deeper (`plugins/flow-next/codex/skills/...` vs `plugins/flow-next/skills/...`). Check `grep -n "(\.\./" plugins/flow-next/codex/skills/<your-skill>/<file>.md` after sync to verify resolution.
