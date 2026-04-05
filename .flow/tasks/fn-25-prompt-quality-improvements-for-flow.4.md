# fn-25-prompt-quality-improvements-for-flow.4 Plan-sync: maintain traceability table on drift

## Description
Add traceability table maintenance to plan-sync agent. When plan-sync detects drift after a task completes, it should also update the `## Requirement coverage` table in the epic spec if one exists.

**Size:** S
**Files:** `plugins/flow-next/agents/plan-sync.md`

## Change details

In plan-sync.md, after Phase 5 (Update Affected Tasks, lines 107-141), add logic for the traceability table:

In Phase 5, add a sub-step after updating downstream task specs:

```markdown
### Update Traceability Table (if present)

If the epic spec (`.flow/specs/<EPIC_ID>.md`) contains a `## Requirement coverage` table:

1. Read the current table
2. If the completed task's scope changed (new files, different requirements covered), update the Task(s) column
3. If drift means a requirement is no longer covered by this task, note it in Gap justification
4. Edit the epic spec to update the table

**Only update entries affected by drift. Don't rewrite the entire table.**
```

Also update Phase 6 (Return Summary) to include traceability table updates in the output:

```
Updated traceability:
- R2 (Session persistence): removed fn-1.2 coverage (API changed), now needs fn-1.4
```

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/agents/plan-sync.md:107-141` — Phase 5 where edits happen
- `plugins/flow-next/agents/plan-sync.md:142-170` — Phase 6 return summary

## Key context

- Plan-sync already edits `.flow/tasks/*.md` and `.flow/specs/` — adding epic spec table edits is within existing scope
- Plan-sync uses the Edit tool (not Write) — same pattern for table updates
- The table format is simple markdown — no parsing complexity
- If no traceability table exists, skip entirely (backward compatible)
## Acceptance
- [ ] Plan-sync checks for `## Requirement coverage` table in epic spec
- [ ] Table updated when drift affects requirement-to-task mapping
- [ ] Only affected rows updated — not full table rewrite
- [ ] Return summary includes traceability changes
- [ ] Gracefully skips if no traceability table exists (backward compatible)
- [ ] No changes to plan-sync's tool access or edit scope rules
## Done summary
Added traceability table maintenance to plan-sync agent. Phase 5 checks epic spec for `## Requirement coverage` table and updates affected rows on drift; Phase 6 includes traceability changes in return summary. Backward compatible — skips if no table exists.
## Evidence
- Commits: 3191d38
- Tests: manual: verified plan-sync.md structure, backward compat (skip if no table)
- PRs: