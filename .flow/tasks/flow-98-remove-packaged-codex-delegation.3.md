---
satisfies: [R5, R9]
---
# flow-98-remove-packaged-codex-delegation.3 Migration message plus the two things that survive in prose

## Description
Carry forward the two things worth keeping when the machinery goes: the measured tier advice that motivated the feature, and the safety rule the packaged path enforced.

**Size:** S/M
**Files:** `plugins/flow-next/templates/usage.md` (bridge recipe section: the safety rule and the tier advice), `.flow/usage.md` (dogfood copy - parity-tested)
**Touches:** [plugins/flow-next/templates/usage.md, .flow/usage.md]

### Approach
- The removed-key advisory itself lives with the key deletion (task .1); this task owns only the prose survivors.
- Safety rule to state where the bridge recipes live: a bridged child writes code; the host keeps git, judgment, and the verdict. This is what the packaged path enforced mechanically and prose must now carry. Without it every recipe is an unbounded second agent.
- Tier advice, without benchmark tables: a value-tier implementer matched a strong-tier one on correctness at roughly two-thirds the wall on well-specified work, so prefer the value tier for clear specs and escalate for gnarly ones. No numbers presented as scores, no model names.
- Keep the dogfood usage copy in step - it is parity-tested against the template.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/templates/usage.md` bridge-recipe section - where the two survivors belong
- `plugins/flow-next/tests/test_dogfood_template_parity.py` - the copy that must stay in step

### Acceptance
- [ ] Usage guide states the bridge safety rule (child writes code; host keeps git, judgment, verdict) and the tier advice with no benchmark table and no model names
- [ ] Dogfood usage copy in step; parity test green
- [ ] Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_dogfood_template_parity test_usage_stages -q`

## Acceptance
- [ ] TBD

## Done summary
Carried the two prose survivors of the removed packaged delegation into the usage guide's bridge-recipe section: an up-front safety rule (the bridged child writes code; the host keeps git, judgment, and the verdict; no recursive bridging) and tier guidance (value tier matches strong tier on correctness at ~2/3 the wall on well-specified work - escalate only for gnarly tasks), with no benchmark table and no model names. Removed the deleted `delegate:codex` / `work.delegate*` vocabulary from the shortcuts block and the prompted-orchestration examples, and kept the dogfood `.flow/usage.md` copy byte-identical.

Gates: focused suites green (test_dogfood_template_parity, test_usage_stages); ruff green. Full suite is RED on the branch for inherited reasons only (codex mirror not regenerated after tasks .1/.2; test_ralph_guard_codex_delegation still present) - owned by tasks .4/.5, untouched by this diff.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)

stage: impl-review - ran (host backend, fresh fable-5 reviewer, SHIP round 1)stage: plan-sync - ran (drift: no; .4/.5 unchanged; cross-spec check deferred to conductor pre-.5)

## Evidence
- Commits: 99f65f38913af1af3233cc9f3072f77b79e29be5
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_dogfood_template_parity test_usage_stages -q (OK, 7 tests), uvx ruff@0.16.0 check . (All checks passed), python3 scripts/run_tests_parallel.py (RED - inherited: codex mirror not regenerated after tasks .1/.2, plus test_ralph_guard_codex_delegation still present; owned by tasks .4/.5), impl-review: host backend SHIP (reviewer claude-fable-5, fresh read-only subagent; receipt /tmp/impl-review-receipt-flow-98-remove-packaged-codex-delegation.3.json; triage said docs-only skip, full review run deliberately - R9 prose is the deliverable)
- PRs: