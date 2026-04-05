# fn-25-prompt-quality-improvements-for-flow.3 Epic-review: add code-to-spec reverse coverage check

## Description
Add code→spec reverse coverage check to epic-review workflow. Currently only checks forward (spec→code: "is every requirement implemented?"). Add reverse direction: "are there changes in the diff that don't trace back to a spec requirement?"

**Size:** S
**Files:** `plugins/flow-next/skills/flow-next-epic-review/workflow.md`

## Change details

In workflow.md Phase 3 (Execute Review), the review prompt (lines 199-238) currently has a "Two-Phase Approach" — Phase 1: Extract Requirements, Phase 2: Verify Implementation.

Add **Phase 3: Reverse Coverage** to the review prompt template:

```markdown
**Phase 3: Reverse Coverage (Code → Spec)**
For each new/modified file in the changed files list:
- Identify which epic requirement it serves
- Flag any file that doesn't trace to a spec requirement

Classification for untraced changes:
- `UNDOCUMENTED_ADDITION` — new functionality not in spec (scope creep)
- `LEGITIMATE_SUPPORT` — refactoring/infrastructure needed to implement a requirement (OK)
- `UNRELATED_CHANGE` — changes outside epic scope (may be accidental)

Report untraced changes but don't auto-reject. UNDOCUMENTED_ADDITION is a flag for acknowledgment, not automatic NEEDS_WORK.

If the epic spec has a `## Requirement coverage` traceability table, use it as the primary reference for mapping files to requirements.
```

Also update the "What to Check" list (lines 215-219) to add:
- Scope creep (code changes that don't trace to spec requirements)

And update the "What NOT to Check" list to add:
- Legitimate refactoring needed to implement requirements (flag but don't block)

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-epic-review/workflow.md:199-238` — current review prompt template

**Optional**:
- `plugins/flow-next/skills/flow-next-epic-review/SKILL.md` — entry point (no changes needed but read for context)

## Key context

- The review prompt is embedded in a heredoc that gets sent to RP or Codex
- Both RP and Codex backend workflows use the same prompt template
- Codex backend (lines 46-76) has its own simpler flow — update both if the Codex backend has a separate prompt section
- The Codex backend uses `flowctl codex completion-review` which embeds its own prompt — check if that needs separate handling
## Acceptance
- [ ] Phase 3 (Reverse Coverage) added to review prompt template
- [ ] Three classification types documented (UNDOCUMENTED_ADDITION, LEGITIMATE_SUPPORT, UNRELATED_CHANGE)
- [ ] "What to Check" list updated with scope creep detection
- [ ] Traceability table referenced as primary mapping source (when present)
- [ ] Reverse coverage is advisory — doesn't auto-block on UNDOCUMENTED_ADDITION
- [ ] Both RP and Codex backend prompts updated (or noted if Codex uses embedded prompt)
- [ ] No changes to verdict parsing logic (still SHIP/NEEDS_WORK)
## Done summary
Added Phase 3 (Reverse Coverage) to epic-review prompt — maps changed files back to spec requirements, flags untraced changes as UNDOCUMENTED_ADDITION/LEGITIMATE_SUPPORT/UNRELATED_CHANGE. Advisory only. Codex backend prompt in flowctl.py not updated per epic constraint (zero CLI changes).
## Evidence
- Commits: 3191d387b60fe5f94b6fd9463932bf6635317090
- Tests: manual: verified diff scoped to workflow.md only
- PRs: