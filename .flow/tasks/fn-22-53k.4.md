# fn-22-53k.4 skill: flow-next-epic-review SKILL.md + workflow.md

## Description

Create `/flow-next:epic-review` skill following impl-review pattern exactly.

**New directory:** `plugins/flow-next/skills/flow-next-epic-review/`

**Files to create:**

1. **`SKILL.md`** - Main skill definition:
   - Role: Epic Review Coordinator (NOT the reviewer)
   - Backends: RepoPrompt (rp) or Codex CLI (codex)
   - Backend detection: args > env > config > error
   - Input: `fn-N [--review=rp|codex|none]`
   - Verdict tags: `<verdict>SHIP|NEEDS_WORK</verdict>` (same as impl-review)

2. **`workflow.md`** - Detailed phases:
   - **RP backend**: setup-review → select files (epic spec + task specs + changed code) → chat-send
   - **Codex backend**: `$FLOWCTL codex completion-review`
   - **Fix loop** (same as impl-review): NEEDS_WORK → agent implements missing requirements → re-review → repeat until SHIP
   - Receipt writing

3. **`flowctl-reference.md`** - Quick command reference (copy from impl-review)

**CRITICAL: Follow impl-review patterns exactly:**
- Study `plugins/flow-next/skills/flow-next-impl-review/SKILL.md` and `workflow.md`
- Use manual prompt building for RP (do NOT use `--response-type review` — it breaks verdict parsing)
- Same verdict tags: `SHIP` / `NEEDS_WORK` (not COMPLETE/GAPS_FOUND)
- Same receipt format structure

**Key differences from impl-review:**
- Scope: entire epic (all tasks) vs single task
- Review focus: spec compliance only (not code quality)
- On NEEDS_WORK: agent fixes gaps inline, re-reviews (same as impl-review; gap tasks only for complex cases)

**Pattern reference:** `plugins/flow-next/skills/flow-next-impl-review/`

## Acceptance

- [ ] `/flow-next:epic-review fn-N` triggers skill
- [ ] Skill supports `--review=rp|codex|none` argument
- [ ] RP backend: sets up review, adds files, sends prompt
- [ ] Codex backend: calls `flowctl codex completion-review`
- [ ] Writes receipt when `REVIEW_RECEIPT_PATH` set
- [ ] Skill registered in `plugin.json`

## Done summary
Created flow-next-epic-review skill with SKILL.md, workflow.md, and flowctl-reference.md. Supports rp/codex backends with same verdict tags (SHIP/NEEDS_WORK), fix loop pattern, and receipt format as impl-review.
## Evidence
- Commits: 15d4379, 274594c, 807c4a6
- Tests: smoke_test.sh
- PRs: