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
Fixed the review-backend plumbing across the RP review skills (canonical files only; mirror regen deferred to fn-81.4). All four RP prompt-assembly sites + export-context now build prompts by deterministic file composition (`rp prompt-get`/`flowctl show`/`flowctl cat` captured via redirection into literal unique prompt files; zero `[PASTE ...]` content-re-typing placeholders remain — surviving bracket slots are scalar-only: [SPEC_ID], [BRANCH_NAME], [LIST TASK IDs], [LIST CHANGED FILES], [COMMIT SUMMARY], [USER'S FOCUS AREAS]). RP review responses now enter context exactly once in all three handlers (impl-review, spec-completion-review, plan-review): chat-send stdout redirects to a unique response file, Read once; verdict + receipt tallies grep the file. The fix-loop iteration cap (MAX_REVIEW_ITERATIONS, default 3, counter + break + escalate) is hoisted into the backend-agnostic fix loops of impl-review/plan-review/spec-completion-review SKILL.md with workflow-codex/copilot/cursor deferring to it (rp behavior preserved; plan-review's RP loop gains the previously-missing cap). Both RP fix loops replace `git add -A` with snapshot-scoped staging (porcelain pre/post set-diff staging only fixer-touched paths; pre-dirty collision rule defers findings whose paths were already dirty — pipeline validated live incl. modified/untracked/deleted/renamed/space-in-name). All touched temp paths unique per the path-persistence rule (review prompts, responses, re-review, updated-plan, export-prompt, snapshots, flowctl-reference examples). Enumeration sweep run: no doc implies the cap or backends are rp-only (pre-existing ralph.md backend-enum drift noted, out of scope). RP impl-review: NEEDS_WORK (send blocks borrowed $PROMPT_FILE across tool-call boundary — fixed by re-declaring both literal paths per block) then SHIP; pitfall captured to memory.
## Evidence
- Commits: 76a8a161f0e1, 23797981045b26a0d6ded979dae472d0dc48305a
- Tests: uv run --with pytest python3 -m pytest plugins/flow-next/tests/ -q (1393 passed, 2 skipped, 164 subtests — run pre- and post-fix), bash scripts/sync-codex.sh x2 (idempotent, validators green; mirror regenerated locally, restored, NOT committed — fn-81.4 owns regen), grep -rn '\[PASTE' plugins/flow-next/skills/ → empty, grep sweep /tmp/review-prompt.md|/tmp/re-review.md|/tmp/updated-plan.md|/tmp/export-prompt.md|/tmp/completion-review-prompt.md in canonical skills → zero hits, live snapshot-staging pipeline test in scratch git repo (modified/untracked/deleted/renamed staged; pre-dirty + pre-untracked excluded), RP impl-review verdict: SHIP (1 fix round; R8/R9/R10/R11/R13 all met, Unaddressed R-IDs: [])
- PRs: