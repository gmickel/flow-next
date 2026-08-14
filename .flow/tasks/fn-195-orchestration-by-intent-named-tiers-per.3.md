---
satisfies: [R2, R6]
---
# fn-195-orchestration-by-intent-named-tiers-per.3 Delete the shipped model identifiers and the pin machinery they fed

## Description
Remove the model identifiers from shipped prose - the count at planning time was 179 mentions across 64 canonical files - and delete the role map and staleness machinery they existed to feed. Two declared exceptions survive: the single tier-guidance page and the review-backend configuration grammar.

**Size:** L (mechanical breadth, low per-edit risk)
**Files:** every canonical file naming a model identifier (docs tree, skills, templates, references) plus `plugins/flow-next/scripts/flowctl.py` (`models.roles` storage, validation, staleness math, the resolve verb) and the schema entry
**Touches:** [plugins/flow-next/docs/**, plugins/flow-next/skills/**, plugins/flow-next/templates/**, plugins/flow-next/references/**, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/schema/flow-config.schema.json, scripts/gen_flow_config_schema.py, .flow/bin/flowctl.py]

### Approach
- Enumerate mechanically first and keep the list: grep the identifier patterns across canonical files, then classify each hit as delete, replace-with-a-tier-name, or declared exception. Do not free-hand the sweep.
- Any identifier that cannot be removed without losing a load-bearing contract is recorded as an exception WITH its reason. A silent survivor is the failure this criterion exists to catch.
- `models.roles` goes entirely: storage, write validation, the staleness stamp and nudge, and the resolve verb. The delegate role is already gone by then; this removes the rest of a surface nothing reads.
- The review backend's own grammar and its receipts are out of scope. Do not touch them.
- Agent definitions keep their model fields - they are the floor, and removing them would change behavior on the primary host.
- Deleted config keys report once and never block, matching the pattern the delegation removal established.

### Investigation targets
**Required** (read before coding):
- the enumerated grep output from this task's first step - the working list
- `plugins/flow-next/scripts/flowctl.py` role-map storage, validation and resolve paths - the deletion boundary
- `plugins/flow-next/tests/test_model_pin_ceremony_prose.py` and the model-resolution tests - what pins the machinery being deleted

### Key context
- This is the task where prose pins bite: every literal removed must be checked against the test corpus and the mirror generator first, with retargets landing in the same commit.

### Acceptance
- [ ] Enumerated hit list recorded with a per-hit disposition; end state is the two declared exceptions and nothing else
- [ ] `models.roles` storage, validation, staleness machinery and resolve verb removed; schema regenerated; drift test green
- [ ] Deleted keys report once, never block; agent model fields untouched
- [ ] Review-backend grammar and receipts untouched
- [ ] Every moved or deleted literal checked against the test corpus and the mirror generator, with retargets in the same commit

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
