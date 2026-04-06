# fn-26-designmd-aware-orchestration.2 Worker: read DESIGN.md in Phase 1.5 when design context present

## Description
Update worker agent to read DESIGN.md sections when task spec has `## Design context`. Fits into existing Phase 1.5 investigation pattern.

**Size:** S
**Files:** `plugins/flow-next/agents/worker.md`

## Change details

In worker.md Phase 1.5 (lines 60-90), add a conditional after reading investigation targets:

```markdown
**If the task spec contains `## Design context`:**

Read `DESIGN.md` (path noted in design context section). Focus on:
- Color tokens referenced in the task's design context
- Component patterns relevant to what you're building
- Do's and Don'ts that apply to this specific UI change

Use design tokens from DESIGN.md, not hard-coded values. If a color, spacing, or component pattern is in the design system, reference it rather than inventing new values.

If DESIGN.md is missing or the path is wrong, note it and proceed — design context is advisory, not blocking.
```

This goes after the existing investigation targets reading (step 1) and before the similar functionality search (step 2), since understanding the design system informs what "similar" means for UI code.

## Investigation targets
**Required:**
- `plugins/flow-next/agents/worker.md:60-90` — Phase 1.5

## Key context
- Phase 1.5 already has the conditional pattern: `**If the task spec contains \`## Investigation targets\`:**` — follow the same pattern for design context
- Worker already has `DESIGN_CONFLICT` escalation category (line 218) — this feeds into it naturally
- Keep it brief — worker reads the task spec's design context summary first, then reads DESIGN.md for full details only for the relevant sections
- Non-blocking — if DESIGN.md is missing, note and continue
## Acceptance
- [ ] Worker reads DESIGN.md when `## Design context` present in task spec
- [ ] Worker focuses on sections relevant to current task (not full file blind read)
- [ ] Worker uses design tokens over hard-coded values
- [ ] Missing DESIGN.md is non-blocking (note and proceed)
- [ ] Conditional placement correct (after investigation targets, before similar-func search)
- [ ] Phase numbering unchanged (still Phase 1.5)
- [ ] Ralph mode unaffected
## Done summary
Added DESIGN.md reading conditional in worker.md Phase 1.5 — reads design tokens/components/dos-donts when task spec has `## Design context`, non-blocking if missing.
## Evidence
- Commits: 5cedb99dd6fbb22c1f7aeb42531414b0f5d732a1
- Tests: smoke_test.sh (52/52 pass)
- PRs: