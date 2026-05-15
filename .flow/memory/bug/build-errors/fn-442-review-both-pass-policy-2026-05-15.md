---
title: "fn-44.2 review: both-pass policy recompute, stale heredoc section names, Strateg"
date: "2026-05-15"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-interview/SKILL.md
tags: [fn-44, scope-flag, impl-review, codex-review, merge-contract, r21-drift-guard, auxiliary-sections, policy-recompute]
problem_type: build-error
symptoms: "Three Majors in one codex NEEDS_WORK round: both-pass docs only show one WRITE_POLICY call; Write Refined Spec heredocs use pre-fn-44 section names contradicting canonical template; Strategy Conflicts missing from 4 auxiliary preservation lists"
root_cause: Multi-phase merge contracts need per-phase policy recomputation (single upfront call is wrong); R21 drift guard catches duplication but not stale-layout contradictions; auxiliary-section enumeration copy-pasted 4x inherited an incomplete original
resolution_type: fix
related_to: [bug/build-errors/agent-rename-epic-id-prompt-key-changes-2026-05-08, bug/build-errors/codex-impl-review-false-positive-on-2026-05-09, bug/build-errors/fn-441-review-cycle-json-contracts-html-2026-05-15, bug/build-errors/template-rewrite-env-var-cascade-2026-05-09]
---

## Problem

T2 of fn-44 (scope-aware interview pass behavior) hit one round of codex NEEDS_WORK before SHIP. Three Major findings clustered around merge-contract documentation precision and template-vs-skill section-name policy:

1. **Both-pass sequencing was under-specified.** Documented `--scope=both` as "biz pass then tech pass" but the `## Compute the write policy` block showed a single `WRITE_POLICY` call with `$SCOPE`. For `SCOPE=both`, phase 2 (tech) needs a freshly-recomputed policy after phase 1 mutates the spec — single pre-edit policy can't correctly decide tech-pass DC shape (biz pass may have promoted FLAT→substructured) or tech-pass placeholder overwrite logic.

2. **Stale legacy heredoc section names in Write Refined Spec.** The illustrative `spec set-plan` heredocs still used `## Problem` / `## Key Decisions` / `## Edge Cases` / `## Acceptance` / `## Open Questions` — pre-fn-44 layout. R21 sync-codex drift guard forbids re-embedding the canonical sequence (`Goal & Context` → `Architecture & Data Models` → `API Contracts`) in skill markdown, so the fix had to thread a needle: drop the legacy section names AND avoid the canonical sequence. Solution: point to `flowctl spec skeleton` + auxiliary sections only.

3. **`Strategy Conflicts` missing from auxiliary preservation lists.** Four preservation lists across the scope-pass section (biz pass, tech pass, both-pass closing, R26 closing) enumerated `Strategy Alignment / Glossary Conflicts / Conversation Evidence / Resolved via Codebase|Project Docs` — but omitted `Strategy Conflicts` even though it's a real auxiliary section the `STRATEGY_AWARE=1` mode creates. A biz-only rerun could clobber existing strategy conflicts.

## What Didn't Work

Initial implementation passed local smoke + R21 drift guard but missed:
- The merge-contract documentation precision for `both`: I conceptualized it as "one policy call covers both phases" because the help text returns one shape, but the policy is per-pass — same shape, different content. Tech pass needs to see the post-biz-pass state to make correct placeholder/DC decisions.
- The R21 guard caught canonical-section duplication but didn't catch "legacy section names that conflict with the new template" — that's a content-semantic check, not a structural one. The drift guard says "don't duplicate the canonical layout," but doesn't say "don't show stale pre-fn-44 layouts that contradict the canonical layout either."
- The auxiliary-section enumeration drift came from copy-paste — the original SKILL.md before this task didn't have `Strategy Conflicts` in every list (it was only mentioned in the Doc-aware behavior (e) discussion). When I authored four new preservation lists, I copied the original incomplete enumeration four times.

## Solution

- **Document policy re-computation for `both`** — the "Compute the write policy" block now explicitly walks two calls: `scope write-policy business` for phase 1, then rebuild `CURRENT_SECTIONS_AFTER_BIZ` (with `biz_pass_ran=true`, `decision_context_has_h3=true`, refreshed `tech_sections_have_content`), then `scope write-policy technical` for phase 2.
- **Heredoc replacement strategy** — replaced the legacy `## Problem` / `## Key Decisions` body with `<canonical body from skeleton>` placeholder comments + only-auxiliary-sections in actual literals. Threads R21 (no canonical sequence in skill) AND removes the pre-fn-44 layout contradiction.
- **Enumeration completeness** — added `Strategy Conflicts` to every auxiliary-section enumeration across all four preservation contexts.

## Prevention

- **Per-pass policy rule** — when a scope-aware skill documents a multi-phase pass, every phase that mutates spec state needs its own policy call. The "compute one policy upfront" pattern is wrong for any scope with phases; flowctl helpers are cheap and stateless — re-call them between phases.
- **Canonical-vs-stale section-name check** — beyond R21 (canonical sequence in skill = forbidden), consider a softer guard: if a skill heredoc shows ANY non-canonical spec section names (`## Problem`, `## Key Decisions`, etc.) when the canonical template has different ones, surface as a lint warning. Hard rule is hostile here (heredocs serve other purposes), but a warning prompts a manual decision.
- **Auxiliary-section enumeration as single source of truth** — currently enumerated 4x in SKILL.md preservation lists. Consider extracting to a single bullet list referenced by each pass section ("preserved auxiliary sections: see X"). Reduces drift risk for any future R that adds a new auxiliary section.
- **Codex catch rate** — codex:gpt-5.5:high caught all three Major findings cleanly with high confidence on a single pass. This is the right backend/spec for fn-44-class documentation-merge-contract reviews.
