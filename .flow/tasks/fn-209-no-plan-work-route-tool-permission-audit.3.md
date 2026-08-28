---
satisfies: [R4]
---
# fn-209-no-plan-work-route-tool-permission-audit.3 pilot --no-plan pass-through

## Description
The pilot half of R4: accept an explicit `--no-plan` on the pilot invocation and forward it to the work dispatch. Default classification stays unchanged (zero tasks -> plan); with the flag, a preceding first-match row classifies the zero-task spec to work so the flag can actually reach the dispatch.

**Size:** S
**Files:** `plugins/flow-next/skills/flow-next-pilot/SKILL.md`, `plugins/flow-next/skills/flow-next-pilot/workflow.md`
**Touches:** [plugins/flow-next/skills/flow-next-pilot/**]

### Approach
- Add a `--no-plan` case to the flag-only Mode Detection parser at `SKILL.md:57-88` (new `PILOT_NO_PLAN` var beside the exports at :87). The parser has NO natural-language path - do not add one; document that pilot takes the flag form only (`set -- $ARGUMENTS` word-splits; never claim verbatim NL passthrough, per the memory lesson).
- Classification (`workflow.md:345-354`, first-match table): add a row `0 tasks exist AND PILOT_NO_PLAN -> work` immediately BEFORE the default `0 tasks exist -> plan` row - without it the default row consumes the case and the flag never reaches a work dispatch. The default row itself stays byte-unchanged, as does every other row.
- Append the flag to the work dispatch line at `workflow.md:446` only when set.

### Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md:57-88` - parser loop + exports
- `plugins/flow-next/skills/flow-next-pilot/workflow.md:440-450` - dispatch invocation lines

### Acceptance
- [ ] `--no-plan` parses into PILOT_NO_PLAN; with it, a zero-task spec classifies to the work dispatch carrying the flag (new first-match row); absent -> classification and dispatch byte-unchanged
- [ ] both cases exercised in the dogfood/verification evidence; no NL parsing added to pilot
- [ ] unknown-flag stderr behavior for other args unchanged
## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
