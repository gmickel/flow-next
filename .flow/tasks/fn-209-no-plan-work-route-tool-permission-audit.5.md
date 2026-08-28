---
satisfies: [R9, R10]
---
# fn-209-no-plan-work-route-tool-permission-audit.5 Routing surfaces + work-rolling refusal + conduct checklists

## Description
Teach the routing surfaces the new route (R9) and add work-rolling's refusal pre-check (R10), plus the conduct-checklist items the repo requires for skill-prose changes.

**Size:** M
**Files:** `plugins/flow-next/docs/pipeline-variations.md`, `plugins/flow-next/docs/running-lean.md`, `plugins/flow-next/skills/flow-next-guide/SKILL.md`, `plugins/flow-next/skills/flow-next-capture/workflow.md`, `plugins/flow-next/skills/flow-next-interview/SKILL.md`, `plugins/flow-next/skills/flow-next-work-rolling/SKILL.md`, `agent_docs/conduct/{work,work-rolling,guide,capture,interview}.md`, `GLOSSARY.md`
**Touches:** [plugins/flow-next/docs/pipeline-variations.md, plugins/flow-next/docs/running-lean.md, plugins/flow-next/skills/flow-next-guide/**, plugins/flow-next/skills/flow-next-capture/workflow.md, plugins/flow-next/skills/flow-next-interview/SKILL.md, plugins/flow-next/skills/flow-next-work-rolling/SKILL.md, agent_docs/conduct/**, GLOSSARY.md]

### Approach
- pipeline-variations.md: new variant row in the table (:31-37) + its own `###` section between "Feature, requirements known" (:50-59) and "Small task" (:61-75), following the Signal -> diagram -> prose shape; cross-link the GLOSSARY "No-plan route" entry (currently an orphan).
- guide matrix (`flow-next-guide/SKILL.md:41-55`): add the route between rows 51-52 ("ready spec, small bounded surface, work directly - no plan"). Router staleness is a defect per :63.
- capture (`flow-next-capture/workflow.md:666-674`): the legal-targets CLOSED LIST must explicitly admit the no-plan route for near-zero-risk fully-known specs; keep chart excluded.
- interview (`flow-next-interview/SKILL.md:449` - shifted +3 by fn-208): extend the "spec without tasks -> /flow-next:plan" hint with the no-plan alternative.
- running-lean.md `:3`/`:16`: verify the `spec -> plan -> work` framing still reads as the default; add at most a one-line pointer to the variant. No layer-table row (no config key exists).
- work-rolling (`flow-next-work-rolling/SKILL.md`, BEFORE the :37 "follow canonical in full" line): pre-check refusing `--no-plan`/NL no-plan with the stated reason (single implicit task degenerates the rolling frontier) and a redirect to plain work - style-match the planSync guardrail at :49. Canonical Phase 1 cannot know it runs under rolling; the refusal must live here.
- conduct checklists (single-checkbox grammar ending "...has broken this"; fn-208 grew work.md by 4 items and touched interview.md - APPEND, never re-derive or reorder existing items): work.md - zero-task fork/ask/pre-answer/minimal-mint item(s); work-rolling.md - refusal bullet; guide.md - matrix covers the route; capture.md - Recommended-next may name it; interview.md - next-step hint includes it; pilot.md - the --no-plan pass-through row (this task owns conduct/**, so the pilot checklist item lands here, not in task 3).
- GLOSSARY "No-plan route" entry: re-verify wording against shipped behavior; add cross-links.

### Investigation targets
**Required:**
- `plugins/flow-next/docs/pipeline-variations.md:31-76` - table + section shapes
- `plugins/flow-next/skills/flow-next-capture/workflow.md:660-680` - closed-list sentence
- `plugins/flow-next/skills/flow-next-work-rolling/SKILL.md:30-55` - execution contract + guardrail style

**Optional:**
- `agent_docs/conduct/README.md` - checklist conventions

### Acceptance
- [ ] pipeline-variations has the sixth variant (table row + section) cross-linked to GLOSSARY
- [ ] guide matrix, capture legal-target list, interview hint each name the route
- [ ] work-rolling refuses no-plan with reason + redirect, before delegating to canonical phases
- [ ] all five conduct checklists carry the new items in house grammar
- [ ] running-lean framing verified; docs-only edits, no version bump

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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
