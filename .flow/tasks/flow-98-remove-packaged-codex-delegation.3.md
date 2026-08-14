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
TBD

## Evidence
- Commits:
- Tests:
- PRs:

**Wave note:** this task touches the dogfood copy under `.flow/`, which is in the always-serial set, so it never waves - that is deliberate, because splitting the template from its parity-checked copy would leave the parity test red between tasks.
