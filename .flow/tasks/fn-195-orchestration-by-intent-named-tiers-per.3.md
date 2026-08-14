---
satisfies: [R2, R3, R6]
---
# fn-195-orchestration-by-intent-named-tiers-per.3 Delete the shipped model identifiers and the pin machinery they fed

## Description
Remove the model identifiers from shipped prose - the count at planning time was 179 mentions across 64 canonical files - and delete the role map and staleness machinery they existed to feed. Two declared exceptions survive: the single tier-guidance page and the review-backend configuration grammar.

**Size:** L (mechanical breadth, low per-edit risk)
**Files:** every canonical file naming a model identifier (docs tree, skills, templates, references) plus `plugins/flow-next/scripts/flowctl.py` (`models.roles` storage, validation, staleness math, the resolve verb) and the schema entry; also `plugins/flow-next/commands/uninstall.md` and `plugins/flow-next/skills/flow-next-setup/workflow.md` (two staleness items `.2` left unowned — see below)
**Touches:** [plugins/flow-next/docs/**, plugins/flow-next/skills/**, plugins/flow-next/templates/**, plugins/flow-next/references/**, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/schema/flow-config.schema.json, scripts/gen_flow_config_schema.py, .flow/bin/flowctl.py, plugins/flow-next/commands/uninstall.md]

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
- the tests that currently pin the `models.roles` pin-ceremony machinery being deleted (storage, validation, staleness stamp, resolve verb) - `plugins/flow-next/tests/test_model_pin_ceremony_prose.py` no longer exists in the tree as of `.2`'s landing; locate its replacement/successor (or confirm no test currently covers this surface) before deleting the machinery, so removal doesn't leave a dangling red test elsewhere <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.2 - the named investigation-target file is stale, it does not exist on disk -->
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md` (the "How to pin" table, ~lines 129-135) - PRE-EXISTING, flagged by .1's plan-sync note as unowned: it carries a concrete model identifier (`grok-4.6`) in scope for R2, and it enumerates spawn primitives per host (Claude native subagent `model` param, Codex `spawn_agent`, etc.) in violation of R3 ("no skill names a spawn primitive"). This task is the natural owner (Touches already includes `skills/**`) - move the per-host mechanism content into the reach pages `.1` wrote under `plugins/flow-next/docs/reach/` and leave the table referring to a tier + "see the reach page for this host," not a spawn call. <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.1 flagged this pre-existing R3 gap with no downstream owner -->
- `plugins/flow-next/commands/uninstall.md` line ~70 - stale description: it still says the model-routing scaffold block "contains a markdown table," but `.2` changed the block to a fully commented HTML-comment example (no table). Correct the parenthetical to describe the actual shape. <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.2 explicitly handed this staleness item downstream, no test currently pins the wording -->
- `plugins/flow-next/skills/flow-next-setup/workflow.md` Review question for `PLATFORM=grok` (~lines 548-563) - still names the concrete slug `grok-4.5` twice ("Grok's only native model family is grok-4.5", "single-native-family (grok-4.5)"). This is not one of R2's two declared exceptions (the tier-guidance page, the review-backend grammar) - it is prose in the setup skill describing family-detection logic, not a review-backend config string. Replace with tier/family language that names no concrete slug, or add it explicitly as a declared exception with its reason if the family-detection logic cannot be stated without the literal. <!-- Updated by plan-sync: fn-195-orchestration-by-intent-named-tiers-per.2 explicitly handed this staleness item downstream, MODEL_SLUG_RE in test_model_routing_scaffold.py only scans the template file so this slug is currently unpinned -->

### Key context
- This is the task where prose pins bite: every literal removed must be checked against the test corpus and the mirror generator first, with retargets landing in the same commit.

### Acceptance
- [ ] Enumerated hit list recorded with a per-hit disposition; end state is the two declared exceptions and nothing else
- [ ] `models.roles` storage, validation, staleness machinery and resolve verb removed; schema regenerated; drift test green
- [ ] Deleted keys report once, never block; agent model fields untouched
- [ ] Review-backend grammar and receipts untouched
- [ ] Every moved or deleted literal checked against the test corpus and the mirror generator, with retargets in the same commit
- [ ] `flow-next-impl-review/workflow-host.md`'s host-pin table: `grok-4.6` identifier removed, spawn-primitive-per-host content moved to the `.1`-authored reach pages (R3)
- [ ] `commands/uninstall.md`'s "contains a markdown table" description corrected to match the commented-block shape `.2` shipped
- [ ] `flow-next-setup/workflow.md`'s Grok review-menu option no longer names the `grok-4.5` slug (or the identifier is recorded as a declared exception with its reason)

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
