---
satisfies: [R8, R9, R10, R11, R13]
---

## Description

Fix the review-backend plumbing: (a) file composition replaces content-re-typing placeholder heredocs at all four RP prompt-assembly sites + export-context; (b) RP review responses enter context exactly once in ALL three handlers (impl-review, spec-completion-review, plan-review); (c) fix-loop iteration cap (counter + break/escalate) in the backend-agnostic common loop with codex/copilot/cursor backend files deferring to it; (d) snapshot-scoped staging instead of `git add -A` in both RP fix loops; (e) unique temp paths per the path-persistence rule. CANONICAL FILES ONLY — mirror regen is fn-81.4's. Depends on fn-81.1 (proof point).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan-review/{workflow.md,SKILL.md}`, `plugins/flow-next/skills/flow-next-impl-review/{workflow-rp.md,workflow-common.md,workflow-codex.md,workflow-copilot.md,workflow-cursor.md,SKILL.md}`, `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md`, `plugins/flow-next/skills/flow-next-export-context/SKILL.md`

## Approach

- **File composition (spec §Approach 2):** per site — `PROMPT_FILE=<literal unique path>`; `$FLOWCTL rp prompt-get ... > "$PROMPT_FILE"`; static criteria appended via quoted heredoc; `$FLOWCTL show <id> >> "$PROMPT_FILE"`. Sites: plan-review workflow.md:305-325, impl-review workflow-rp.md:85-109, spec-completion-review workflow-rp.md:88-112, export-context SKILL.md:82-93 (prompt-get at :82 is a bare print — redirect it). Scalar placeholders (`[SPEC_ID]`, `[BRANCH_NAME]`, `[USER'S FOCUS AREAS]`) may remain; content-re-typing placeholders (`[PASTE ...]`, `[PASTE SPEC]`) may not.
- **Single-entry responses (spec §Approach 3), ALL THREE handlers:** impl-review workflow-rp.md:191-192, spec-completion-review's rp response handling, AND plan-review workflow.md:383-397 — redirect chat-send stdout to a unique response file, Read it once (parse + fix-loop context), verdict/tally extraction greps the file. Do NOT just delete echoes — command substitution hides stdout; the file+Read IS the single entry.
- **Cap hoist:** counter + break-to-escalation in the backend-agnostic Fix Loop (impl-review SKILL.md:333-362 and/or workflow-common.md); `workflow-codex.md:39-44` ("Repeat until SHIP"), `workflow-copilot.md`, `workflow-cursor.md` updated to defer to the bounded common loop; rp behavior preserved (workflow-rp.md:332). Default 3, `MAX_REVIEW_ITERATIONS` env honored. Escalation on cap: surface findings + stop (matches rp). Enumeration sweep (`grep -rniE 'rp.{0,3}codex.{0,3}copilot|review.backend'` — include cursor in the check; memory entry adding-a-review-backend-sweep-all) so no doc/table implies rp-only.
- **Snapshot-scoped staging (both rp fix loops — impl-review workflow-rp.md:341, completion-review workflow-rp.md:449):** record `git status --porcelain` BEFORE the fix; after the fix, diff the snapshots and stage ONLY paths that changed between them (modified, untracked, deleted, renamed all covered). If a fixer-modified path was ALREADY dirty pre-fix, do NOT stage it — surface the collision and defer/escalate that finding (never sweep pre-existing hunks). Mirrors land's staging discipline.
- **Unique temp paths** per the path-persistence rule for every path touched here: review prompt files, `/tmp/re-review.md` (impl-review-rp:362, completion-rp:470, plan-review:488), `/tmp/updated-plan.md` (plan-review SKILL.md:257, workflow.md:450), `/tmp/export-prompt.md`, `/tmp/completion-review-prompt.md`. Re-review sends reference the same literal paths established earlier in the flow.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-impl-review/workflow-rp.md:85-200,330-370,440-460` — prompt build, response capture, fix loop, re-review
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md:333-362` + `workflow-common.md` — backend-agnostic fix loop (cap landing zone)
- `plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md` + `workflow-copilot.md` + `workflow-cursor.md` — per-backend loops that must defer to the common cap
- `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md:88-112,440-475`
- `plugins/flow-next/skills/flow-next-plan-review/workflow.md:300-397,440-495`
- `.flow/memory/` entry `adding-a-review-backend-sweep-all-2026-06-29` — enumeration sweep checklist

**Optional:**
- `plugins/flow-next/skills/flow-next-land/workflow.md` — staging discipline to mirror

## Key context

RP keeps parallel rubric copies in skill markdown — this task changes PLUMBING (assembly/response/loop mechanics), never rubric CONTENT. Depends on fn-81.1: reuse its literal-path and single-entry conventions verbatim.

## Acceptance

- [ ] `grep -rn '\[PASTE' plugins/flow-next/skills/` empty; remaining bracket placeholders verified scalar-only (list them in the summary)
- [ ] RP review responses enter context exactly once in all three handlers; fix loops + tallies function from the response files
- [ ] All four backends bounded: common-loop counter + break + escalation, default 3; codex/copilot/cursor files defer to it; enumeration sweep results in summary
- [ ] Both rp fix loops use snapshot-scoped staging (porcelain before/after) with the pre-dirty-path defer rule; no `git add -A` remains in either file
- [ ] All touched temp paths unique per the path-persistence rule; canonical-only diff (no mirror commit)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
