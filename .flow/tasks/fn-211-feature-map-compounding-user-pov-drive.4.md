---
satisfies: [R8]
---
# fn-211-feature-map-compounding-user-pov-drive.4 Registration, repo docs, and the decided docs-site placement

## Description
Finalization: register the skill on every platform surface and ship the repo half of the R8 docs story (the site half is decided in the spec's Docs-integration section and executed in the docs-site repo at release, per the release doc's downstream walk).

**Size:** M
**Files:** `scripts/sync-codex.sh`, `plugins/flow-next/codex/**` (regen), `plugins/flow-next/docs/self-improving.md`, `plugins/flow-next/docs/architecture.md`, `plugins/flow-next/docs/skills.md`, `plugins/flow-next/docs/README.md`, `plugins/flow-next/docs/teams.md`, `plugins/flow-next/README.md`, `agent_docs/conduct/features.md`, `agent_docs/conduct/README.md`, `plugins/flow-next/skills/flow-next-guide/SKILL.md`, `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `plugins/flow-next/tests/test_chart_docs_inventory.py`, `plugins/flow-next/tests/test_command_shim_flatten.py`, manifest description strings
**Touches:** [scripts/sync-codex.sh, plugins/flow-next/codex/**, plugins/flow-next/docs/**, plugins/flow-next/README.md, agent_docs/conduct/**, plugins/flow-next/skills/flow-next-guide/**, README.md, CLAUDE.md, CHANGELOG.md, plugins/flow-next/tests/test_chart_docs_inventory.py, plugins/flow-next/tests/test_command_shim_flatten.py, .claude-plugin/**, plugins/flow-next/.claude-plugin/**, plugins/flow-next/.codex-plugin/**, plugins/flow-next/.cursor-plugin/**]

### Approach
- Walk `agent_docs/adding-skills.md` in full (all steps; full launch, NOT the experimental tier - spec Decision Context). Registration trio: `generate_openai_yaml` call (`scripts/sync-codex.sh:1695-1699` shape; workflow-blue bucket), `REQUIRED_OPENAI_YAML_SKILLS` entry (`:1823`), run sync-codex twice and commit the mirror. No new agent -> opencode allowlist untouched.
- Every count/inventory surface swept: manifest description strings (memory `skill-adding-version-bump-leaves-stale-2026-06-05`), root README Commands clause + counts, plugin README published counts, `docs/teams.md` counts, the `CLAUDE.md` commands/template block, and the count/inventory assertions in `test_chart_docs_inventory.py` + `test_command_shim_flatten.py` (deliberate pin updates with the rationale in the commit - the new skill changes filesystem and published counts).
- Repo docs per the spec's Docs-integration section: self-improving.md gains the feature map as a compounding loop beside memory/glossary/decisions/strategy (the most load-bearing edit - keep count language evergreen); architecture.md `.flow/` layout gains a features subsection beside the charts one (note: tracked/committed, no flowctl validation - unlike memory); skills.md roster row + count language; docs/README.md index row; QA/drive roster descriptions gain the consumes-map clause.
- Conduct checklist `agent_docs/conduct/features.md` (4-6 falsifiable behaviors keyed to the outcome line + Doctor + never-edits-product-code) + index row.
- Guide routing: one matrix-adjacent line in the guide skill for when to recommend /flow-next:features.
- CHANGELOG under `## Unreleased`, user-outcome-first (no version bump - batched rule).
- Docs framing per `agent_docs/writing-docs.md`: capability-positive titles/leads, bounds stay negative in prose, `## Where it stops` never `## What this is not`, no em dashes in shipped docs, anchors checked (`python3 scripts/check_doc_anchors.py`), relative links only in plugin docs. The `/flow-next:map` disambiguation appears once per page at most ("user-POV drive map" vs "code index").
- Verify at the consumer layout, not just the repo tree (memory `installer-must-own-what-it-deletes-2026-08-21`): after sync, check the mirror's generated skill entry resolves.
- Cold-invocation smoke: one NON-REFUSAL manual seed run against a small real target (a real map seeded, at least one route driven and proven; the refusal path alone does not satisfy this), recorded in the done summary with the seeded map's shape, then the repo FULL gate (`python3 scripts/run_tests_parallel.py` + pinned ruff).
## Acceptance
- [ ] sync-codex.sh registration trio complete; mirror regenerated twice, idempotent, guards green
- [ ] All adding-skills.md steps walked (full launch); every count surface swept: manifests, root README, plugin README, docs/teams.md, CLAUDE.md block, and the two count-pinning test files updated deliberately
- [ ] Repo docs edits from the spec's Docs-integration section landed; anchors + docs-link checks green
- [ ] Conduct checklist + index row; guide routing line present
- [ ] CHANGELOG Unreleased entry, user-outcome-first, no version bump
- [ ] Non-refusal cold seed smoke recorded (real map, at least one proven route); full gate green
- [ ] Site placement remains fully specified in the spec (executed at release) - no site edits from this repo task
## Done summary
Finalization: registered flow-next-features across the codex-mirror machinery (generate_openai_yaml call, DIET surfaced description, REQUIRED_OPENAI_YAML_SKILLS entry; mirror regenerated idempotently), swept every count surface deliberately (filesystem 33 skills / 29 commands, published 32 skills / 27 slash excluding the rolling beta: both count-pinning test files updated with the fn-211.4 rationale, plus root README, plugin README, docs/skills.md, docs/teams.md, docs/README.md, CLAUDE.md Where-to-look row, and manifest description strings), and shipped the repo half of the R8 docs story: self-improving.md gains the feature map as a compounding loop (table row + full seeded/grows/read-by/pruned section, count language made evergreen), architecture.md gains the features layout subsection, skills roster + docs index rows with consumes-map clauses on the qa/drive rows, the conduct checklist page + index row, the guide routing matrix row, and the user-outcome-first CHANGELOG entry under Unreleased. The site half of R8 stays decided-in-spec, executed at release per the release doc's downstream walk. Conductor review fix: one duplicated CLAUDE.md table row deduped (9c62a3e5). Grok-4.6 bridge implementation; conductor in-host review verdict SHIP; focused suites (38), doc anchors, and triple sync-codex idempotency green.

stage: plan-sync - skipped(config: planSync.enabled != true)
stage: impl-review - ran (in-host, verdict SHIP; one fix commit 9c62a3e5) (model: claude-fable-5)
## Evidence
- Commits: 79a1d9a7, 9c62a3e5
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_features_skill_contract test_command_shim_flatten test_chart_docs_inventory -q  # 38 OK (integrated target), python3 scripts/check_doc_anchors.py  # OK, ./scripts/sync-codex.sh x3  # exit 0, idempotent
- PRs: