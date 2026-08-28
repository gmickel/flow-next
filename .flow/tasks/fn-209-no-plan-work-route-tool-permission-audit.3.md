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
- Add a `--no-plan` case to the flag-only Mode Detection parser at `SKILL.md:61-92` (new `PILOT_NO_PLAN` var beside the exports at :91; parser shape unchanged post-fn-208, just +4 lines above it). The parser has NO natural-language path - do not add one; document that pilot takes the flag form only (`set -- $ARGUMENTS` word-splits; never claim verbatim NL passthrough, per the memory lesson).
- Classification (`workflow.md:345-354`, first-match table): add a row `0 tasks exist AND PILOT_NO_PLAN -> work` immediately BEFORE the default `0 tasks exist -> plan` row - without it the default row consumes the case and the flag never reaches a work dispatch. The default row itself stays byte-unchanged, as does every other row.
- Append the flag to the work dispatch line at `workflow.md:446` only when set.

### Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md:61-92` - parser loop + exports
- `plugins/flow-next/skills/flow-next-pilot/workflow.md:440-450` - dispatch invocation lines

### Acceptance
- [ ] `--no-plan` parses into PILOT_NO_PLAN; with it, a zero-task spec classifies to the work dispatch carrying the flag (new first-match row); absent -> classification and dispatch byte-unchanged
- [ ] both cases exercised in the dogfood/verification evidence; no NL parsing added to pilot
- [ ] unknown-flag stderr behavior for other args unchanged
### Acceptance
- [ ] TBD

### Done summary
TBD

### Evidence
- Commits:
- Tests:
- PRs:
## Acceptance
- [ ] TBD

## Done summary
Pilot now accepts an explicit `--no-plan` flag (new `PILOT_NO_PLAN` var in the Mode Detection parser, flag-form only — no NL path added, documented after the parser) and forwards it to the work dispatch: a new first-match classification row routes a zero-task spec to `work` dispatched with `--no-plan` when the flag is set, while the default `0 tasks exist -> plan` row and every other row stay byte-unchanged. The frontmatter description lists the flag; unknown-flag stderr behavior is untouched.

baseline: green (focused pilot-adjacent suites: test_precheck_mode_contract test_pilot_strikes_prose test_pilot_backlog_mirror_safety test_skill_prose_diet test_guide_routing — 74 tests OK pre-edit)
implementer: grok-4.6 bridge (foreground, single clean pass; host verified diff, ran gates, committed)

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
## Evidence
- Commits: c725c16a62eec2aa8ff82c85ff94daa46594764b
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_precheck_mode_contract test_pilot_strikes_prose test_pilot_backlog_mirror_safety test_skill_prose_diet test_guide_routing -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., parser dogfood: extracted Mode Detection block executed with '--spec fn-9 --no-plan' (PILOT_NO_PLAN=1), '--spec fn-9' (PILOT_NO_PLAN=0), '--no-plan --bogus' (unknown-flag stderr unchanged)
- PRs:stage: plan-sync - skipped(config: planSync.enabled != true)
