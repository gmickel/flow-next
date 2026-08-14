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
Setup now proposes a single commented model-routing block (four tier names, grammar and resolution order as comments, zero model identifiers) written verbatim after the Docs step; an existing block is left untouched and reported, and the closing line names the file and invites an edit. The probe-and-pin ceremony, the routing question and its three host question references, the three routing implementation references, the staleness stamp and the review-backend switch offer are deleted, not skipped.

stage: impl-review - skipped(policy: host-deferred + parallel wave - conductor owns the gate)
stage: delegation - skipped(config: delegation off)


Integrated onto spec branch as 45379f2c; review fixes a67390ce (smoke fn-88.4 retargeted to routing-block contract, docs-decline + headless hard outs, unmarked-routing-prose guard) + ROUTING_OUTCOME enum extension in the completion commit.

stage: impl-review - ran (host backend, fresh fable-5 reviewers; r1 NEEDS_WORK -> fixes a67390ce -> r2 SHIP)
## Evidence
- Commits: 45379f2c5c32edd58ff2c06fcd542a726f0bf6bf, a67390ceba07989b643b2acafbc9592bd73fd4ad
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_model_routing_scaffold test_setup_reference_routing test_setup_cursor_host test_setup_grok_host, cd plugins/flow-next/tests && python3 -m unittest test_setup_block_helper test_setup_mode_stamp test_setup_snippet_lockstep test_setup_spec_discovery_hits test_cursor_host_docs test_host_review_backend test_reference_encoding_guard test_skill_prose_diet test_prompt_text_pinned test_rp_setup_workflow_contract, python3 scripts/run_tests_parallel.py (files=191 ran=4401 failures=0 errors=0), uvx ruff@0.16.0 check ., integrated verify: python3 scripts/run_tests_parallel.py @a67390ce content (191 files, 4401 tests, 0F 0E) + ruff clean; post-enum-fix focused: test_model_routing_scaffold test_setup_reference_routing test_setup_cursor_host test_hot_path_sweep (OK), impl-review: host backend r1 NEEDS_WORK (P1 smoke red + P2 ladder outs + P3 unmarked block), r2 SHIP (reviewer claude-fable-5, fresh subagents; receipt /tmp/impl-review-receipt-fn-195-orchestration-by-intent-named-tiers-per.2.json)
- PRs: