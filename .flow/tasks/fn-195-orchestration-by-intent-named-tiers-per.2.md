---
satisfies: [R5]
---
# fn-195-orchestration-by-intent-named-tiers-per.2 Setup proposes a commented routing block and stops asking pin questions

## Description
Replace setup's model-pin ceremony with a single proposal: write a commented routing block into the project instruction file, then say it was written and invite an edit. Setup stops probing CLIs for verbatim slugs and stops asking routing questions.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-setup/workflow.md` (the routing question flow and pin ceremony), `references/model-pins.md`, `references/model-routing-*.md`, `templates/model-routing-snippet.md` (becomes the commented block), plus setup's closing summary
**Touches:** [plugins/flow-next/skills/flow-next-setup/**]

### Approach
- The block ships with values commented out and tier guidance as comments. It must be obvious at a glance that these are the consumer's preferences to fill, not detected facts. Never write a detected model into it - that is the config-that-lies failure the project already rejected once.
- An existing block a human has edited is left alone and reported. Idempotency matters here: setup is re-run after every release.
- Delete the probe-and-pin ceremony rather than softening it: no verbatim-appearance requirement, no probe output parsing for pins, no staleness stamp, no routing menu. The discover-then-invoke habit lives in the reach pages, where it belongs.
- Setup's closing line names what it wrote and asks for an edit - one sentence, in the same register as its other closing lines.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-setup/workflow.md` - the question flow and where the pin ceremony sits
- `plugins/flow-next/skills/flow-next-setup/templates/model-routing-snippet.md` - the current snippet, which becomes the commented block
- the setup-block helper's idempotency contract - a re-run must not disturb an edited block

### Acceptance
- [ ] Setup writes a commented routing block with tier guidance as comments and no detected values
- [ ] An existing or human-edited block is left untouched and reported
- [ ] Probe-and-pin ceremony, routing menu and staleness stamp removed - not merely skipped
- [ ] Closing line names the file it wrote and invites an edit
- [ ] Focused suites green: setup-block, setup-mode, model-routing-scaffold and host-detection tests

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
