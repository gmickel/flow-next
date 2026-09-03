---
satisfies: [R10]
---
# fn-219-pilot-stage-chaining-and-land-patience.4 Docs, setup notes, and CHANGELOG Unreleased entry for both opt-in keys

## Description
Document the two keys where users read them (R10): the flowctl config table, the orchestration chaining section, the running-lean pricing, the setup summary's optional-layer notes, and a user-outcome-first `## Unreleased` CHANGELOG entry. This task also owns the ONE codex-mirror regeneration for the whole spec (the sync script rebuilds the mirror tree from scratch, so it runs once, after every canonical prose task landed) and extends the .2/.3 contract tests to the mirror copies. Depends on .1–.3.

**Size:** M
**Files:** `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/orchestration.md`, `plugins/flow-next/docs/running-lean.md`, `plugins/flow-next/skills/flow-next-setup/workflow.md`, `CHANGELOG.md`, `plugins/flow-next/codex/**` (regenerated), `plugins/flow-next/tests/test_pilot_chain_stages.py`, `plugins/flow-next/tests/test_land_patience_after_review.py`
**Touches:** [plugins/flow-next/docs/flowctl.md, plugins/flow-next/docs/orchestration.md, plugins/flow-next/docs/running-lean.md, plugins/flow-next/skills/flow-next-setup/workflow.md, CHANGELOG.md, plugins/flow-next/codex/**, plugins/flow-next/tests/test_pilot_chain_stages.py, plugins/flow-next/tests/test_land_patience_after_review.py]

### Approach
- `flowctl.md` config table: a `pipeline.chainStages` row beside `pipeline.qa` (`:1084`) in that row's register (strict string-enum, the one-row chain table, why `plan → plan-review` is not a row, what never chains, off = byte-for-byte today, earns its keep only with `pipeline.qa` on) and a `land.patienceMinutesAfterReview` row beside `land.patienceMinutes` (`:1075`): silence-only, the four conditions, replace-not-min semantics (a late review can lengthen the wait — grace after the review), off states incl. `0`, report token `anchor=`.
- `orchestration.md` "Chaining the loops" (`:358-379`): add a short subsection distinguishing chaining ACROSS ticks (the existing driver composition) from chaining WITHIN a tick (`pipeline.chainStages`), plus one paragraph on `land.patienceMinutesAfterReview` as the wait the driver no longer pays after a clean head-current review — and why it stays opt-in (human-objection grace).
- `running-lean.md` "Autonomous loops" (`:150-157`): price both in structural shapes (no timings): chaining trades one driver re-anchor for a longer single tick, only on QA-enabled repos; patience-after-review trades push-anchored grace for review-anchored grace. Add both keys to the layers table's autonomous-loops row so the table stays the index.
- `flow-next-setup/workflow.md` Notes block (`:936`): one line per key in the existing `pipeline.qa` line's shape.
- `CHANGELOG.md`: insert `## Unreleased` above 4.12.0 with an opening user-outcome paragraph (who benefits: unattended pilot/land operators; what changed: fewer idle loop intervals; what control they keep: both off by default, no gate or merge license changes; the two keys are independently toggleable) then two `### Added` bullets per `agent_docs/releasing.md` ordering + hard rejection test, and one sentence recording that the plan→plan-review pair was found redundant (the plan stage already embeds its review); end with `(fn-219)`. No version bump.
- Mirror: run `./scripts/sync-codex.sh` TWICE (idempotent — second run must produce no diff) and commit the regenerated `plugins/flow-next/codex/**`. Then switch the .2/.3 contract tests from canonical-only to the `both_copies` pattern (`test_skill_prose_diet.py:68`) so the mirror copies are pinned too.
- README stage-sequence line (`README.md:232`) — leave as is unless the chaining sentence reads wrong against it; a one-clause note is acceptable, a rewrite is not.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/docs/flowctl.md:1070-1090` — sibling rows
- `plugins/flow-next/docs/orchestration.md:355-380` — the section to extend
- `plugins/flow-next/docs/running-lean.md:45-60,150-157` — table + layer entry
- `agent_docs/releasing.md:70-125` — changelog ordering + rejection test
- `plugins/flow-next/skills/flow-next-setup/workflow.md:925-945` — notes block
- `scripts/sync-codex.sh:140-170` — the mirror rebuild (why it runs once)

**Optional** (reference as needed):
- `agent_docs/writing-docs.md` — capability framing
- `plugins/flow-next/docs/prose.md` — artifact prose contract
## Acceptance
- [ ] Both keys documented in the flowctl config table with defaults, off states, and behaviour
- [ ] orchestration.md distinguishes within-tick vs across-tick chaining and prices patience-after-review's opt-in rationale
- [ ] running-lean.md prices both in structural terms (no timings)
- [ ] Setup notes carry one line per key
- [ ] `./scripts/sync-codex.sh` run twice, second run clean, mirror committed; .2/.3 contract tests pass on canonical AND mirror copies
- [ ] CHANGELOG `## Unreleased` entry passes the releasing.md hard rejection test; no version bump
- [ ] Full suite green: `python3 scripts/run_tests_parallel.py` and `uvx ruff@0.16.0 check .`
## Done summary
Documented `pipeline.chainStages` and `land.patienceMinutesAfterReview` where users read them (R10): flowctl.md config-table rows beside `pipeline.qa` / `land.patienceMinutes` (strict string-enum, closed one-row chain table with plan→plan-review recorded as dissolved; silence-only re-anchor, four conditions, replace-not-min with the early/late examples, off states incl. `0`, head-current incl. submitted-after-last-push, `anchor=` token), an orchestration.md "Within one pilot invocation vs across driver invocations" subsection plus the opt-in rationale for patience-after-review, running-lean.md structural pricing (layers-table row + autonomous-loops bullet, no timings), two setup Notes lines, and a CHANGELOG `## Unreleased` entry (user-outcome paragraph, two Added bullets, `(fn-219)`, no version bump). Ran the ONE `./scripts/sync-codex.sh` regen for the spec (twice; second run clean) and switched `test_pilot_chain_stages.py` / `test_land_patience_after_review.py` to the `both_copies` pattern (canonical + mirror; mutation-checked red on a mutated mirror, green restored; no assertion weakened). The review's last surviving finding (pilot SKILL.md workflow-summary "Done when" clauses still promising one dispatch / one evidence block) was fixed by the conductor in e9f72901 with a further mirror regen, since it sat on task .2's surface.

baseline: green via handoff (verified at 47f25976 by fn-219.3); ruff green pre-edit.
Verify at f9b863a2: `gate classify` → FULL (force-full prefix plugins/flow-next/codex/); full suite `python3 scripts/run_tests_parallel.py` files=201 ran=4723 failures=0 errors=0 (green receipt minted: .flow/tmp/green-receipts/f9b863a2-unittest.json); `uvx ruff@0.16.0 check .` clean; `gen_flow_config_schema.py --check` current. At e9f72901: focused pin suites (test_pilot_chain_stages, test_land_patience_after_review, test_skill_prose_diet, test_prompt_text_pinned) OK; ruff clean; the full suite re-runs at the conductor's final gate.

stage: impl-review - ran (codex gpt-5.6-sol high; round 1 three-axis fan-out NEEDS_WORK ×3 → merged 4 findings, 3 fixed in 77d39b7a; round 2 NEEDS_WORK, 1 finding fixed by the conductor in e9f72901; round 3 SHIP) (model: codex gpt-5.6-sol at high)
stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: fb52519672828f6f5a15a15e3aa091e5e514b91e, 77d39b7a20aff7990d8b66abc8c02c783f3e216b, f9b863a2418c494725f0441e8ff56b5e5fabc060, e9f72901
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_pilot_chain_stages test_land_patience_after_review test_skill_prose_diet test_pipeline_qa_config test_land_config test_flow_config_schema test_flow_config_schema_drift test_chart_docs_inventory test_ralph_docs_truth -q, python3 scripts/gen_flow_config_schema.py --check, ./scripts/sync-codex.sh (run twice, second run clean), python3 scripts/run_tests_parallel.py (at f9b863a2: files=201 ran=4723 failures=0), uvx ruff@0.16.0 check .
- PRs: