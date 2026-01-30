# fn-22-53k.8 skill: update flow-next-work for completion_review status

## Description

Update `/flow-next:work` skill to handle `status=completion_review` from selector.

**Changes to `plugins/flow-next/skills/flow-next-work/`:**

1. **`phases.md`** — Add handling for when `flowctl next` returns `status=completion_review`:
   - Detect status after all tasks complete (Ralph.sh line ~943 shows handler pattern: check `status == "completion_review"`)
   - Run `/flow-next:epic-review <epic-id>` command
   - On SHIP: set `completion_review_status=ship`, epic can close
   - On NEEDS_WORK: fix loop runs (same as Ralph)

2. **`SKILL.md`** — Document completion_review behavior in interactive mode

**Pattern reference:** fn-22-53k.5 ralph.sh lines 943-954 shows actual implementation (completion_review status handler runs before final else clause). See also: ralph.md lines 297-354 (epic-completion review gate), flowctl.md lines 103-108 (epic set-completion-review-status command), flowctl.md lines 352-360 (next --require-completion-review flag)

**NOTE:** Without this, interactive `/flow-next:work fn-N` will fail when selector returns `completion_review` after all tasks done. Epic-review skill must exist (fn-22-53k.6 responsibility).

## Acceptance

- [ ] `/flow-next:work fn-N` handles `status=completion_review` from selector
- [ ] Invokes `/flow-next:epic-review` when completion review needed
- [ ] Fix loop runs until SHIP verdict
- [ ] Sets `completion_review_status=ship` after passing review

## Done summary
Updated flow-next-work skill to handle completion_review status. Added Phase 3g in phases.md that checks epic's completion_review_status after all tasks complete, invokes /flow-next:epic-review if needed, and sets status=ship after SHIP verdict.
## Evidence
- Commits: 466b1d2, df2f565
- Tests: smoke_test.sh (45 passed)
- PRs: