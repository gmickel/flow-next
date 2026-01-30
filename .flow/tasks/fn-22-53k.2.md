# fn-22-53k.2 command: epic-review.md shim

## Description

Create command shim for `/flow-next:epic-review` that invokes the skill.

**New file:** `plugins/flow-next/commands/flow-next/epic-review.md`

**Content:** Follow `plan-review.md` pattern exactly:
```markdown
# IMPORTANT: This command MUST invoke the skill `flow-next-epic-review`

The ONLY purpose of this command is to call the `flow-next-epic-review` skill. You MUST use that skill now.

**Arguments:** $ARGUMENTS

Pass the arguments to the skill. The skill handles the review logic.
```

**NOTE:** This replaces the original plan for `flowctl epic-review`. Verdict computation requires LLM; there's no deterministic gap analysis. All review logic lives in the skill or codex command.

**Pattern reference:** `plugins/flow-next/commands/flow-next/plan-review.md`

## Acceptance

- [ ] `plugins/flow-next/commands/flow-next/epic-review.md` exists
- [ ] Command invokes `flow-next-epic-review` skill
- [ ] `/flow-next:epic-review fn-N` triggers skill (after skill is implemented)

## Done summary
Created epic-review.md command shim that invokes flow-next-epic-review skill. Follows plan-review.md pattern.
## Evidence
- Commits:
- Tests: manual: skill invocation verified
- PRs: