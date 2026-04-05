# fn-25-prompt-quality-improvements-for-flow.1 Plan skill: investigation targets, traceability table, early proof point

## Description
Add three new prose sections to the plan skill output: investigation targets per task, requirement coverage traceability table per epic, and early proof point per epic.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan/steps.md`, `plugins/flow-next/skills/flow-next-plan/examples.md`

## Investigation targets (task spec template)

In steps.md around line 262-280 (task spec content template), add `## Investigation targets` section between `## Approach` and `## Key context`:

```markdown
## Investigation targets
**Required** (read before coding):
- `src/auth/oauth.ts` — existing OAuth flow to extend
- `src/middleware/session.ts:23-45` — session validation pattern

**Optional** (reference as needed):
- `src/auth/*.test.ts` — existing test patterns
```

Rules for the planner:
- Max 5-7 targets per task (focus, don't flood)
- Use exact file paths with optional line ranges — not descriptions alone
- Validate paths exist at plan time (repo-scout/context-scout already found them)
- "Required" = must read before implementing. "Optional" = helpful reference.
- Targets come from repo-scout/context-scout findings in Step 1

## Requirement coverage table (epic spec template)

In steps.md Step 5 Route B, after writing epic spec (around line 209-227), add a `## Requirement coverage` section to the epic spec template:

```markdown
## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | OAuth login flow | fn-1.1, fn-1.2 | — |
| R2  | Session persistence | fn-1.3 | — |
| R3  | Admin dashboard | — | Deferred to fn-2 |
```

Rules for the planner:
- One row per acceptance criterion or distinct requirement from the epic spec
- Every requirement must map to at least one task OR have a gap justification
- Table goes at the bottom of the epic spec (after Acceptance, before any References)
- Keep Req IDs simple (R1, R2...) — they're local to this epic

## Early proof point (epic spec template)

In the same epic spec template, add `## Early proof point` section after Acceptance:

```markdown
## Early proof point
Task fn-1.1 validates the core approach (OAuth handshake works end-to-end).
If it fails, re-evaluate the auth strategy before continuing with fn-1.2+.
```

Rules for the planner:
- Identify which task proves the fundamental approach works
- One sentence: which task + what it proves
- One sentence: what to reconsider if it fails
- Usually the first task in dependency order, but not always

## Examples update

In examples.md, add a new section "Good vs Bad: Investigation Targets" showing:

**Bad**: Vague descriptions ("the authentication code"), too many targets (10+), stale paths to files that moved

**Good**: Exact paths with line ranges, max 5 items, Required/Optional tiers, derived from scout findings

Also update the existing "Good: Task spec" example (around line 149-173) to include an `## Investigation targets` section.

Add a brief "Good: Traceability Table" example showing a 3-4 row table with one gap justification.

## Key context

- Task spec template is at steps.md:262-280
- Epic spec template is at steps.md:209-227
- examples.md has paired good/bad examples at ~344 lines
- Planner already runs scouts in Step 1 that produce file:line refs — investigation targets are just structured handoff of those findings
## Acceptance
- [ ] `## Investigation targets` section added to task spec template in steps.md
- [ ] `## Requirement coverage` table added to epic spec template in steps.md
- [ ] `## Early proof point` section added to epic spec template in steps.md
- [ ] Planner rules documented for each new section (max targets, path validation, gap justification)
- [ ] examples.md has good/bad investigation targets examples
- [ ] examples.md good task spec example updated with investigation targets
- [ ] examples.md has traceability table example
- [ ] No changes to flowctl commands or .flow/ schema
- [ ] Existing plan step flow (Step 0-8) unchanged — new sections are additions to output templates only
## Done summary
Added investigation targets (Required/Optional tiers), requirement coverage traceability table, and early proof point sections to plan skill templates and examples.
## Evidence
- Commits: 77e9ff4
- Tests: manual: verified step flow Steps 0-8 unchanged, no schema/hook changes
- PRs: