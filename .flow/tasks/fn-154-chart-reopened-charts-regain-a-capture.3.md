---
satisfies: [R4, R9]
---
# fn-154-chart-reopened-charts-regain-a-capture.3 Docs, glossary, changelog, and the discriminator pin

## Description
Document the new behavior everywhere it is currently described wrongly, pin the discriminator so the docs cannot drift from the code, and stage the release entry.

Each surface below was located by the docs-gap scout; the claim in each is stale in the same way - it says or implies that after a reopen, the next `briefing` call is a no-op.

**Canonical files (hand-edit these):**
- `plugins/flow-next/docs/flowctl.md:1100-1110` - the v1 JSON envelope section, where `error.class`'s enum is exhaustively listed. Document the new discriminator's name and value set here, in the same exhaustive style (R9).
- `plugins/flow-next/docs/flowctl.md:1151-1153` - the `chart briefing` command block (currently documents only `--force`).
- `plugins/flow-next/docs/flowctl.md:1175` - subcommand contract table, `briefing` row: "first non-draft sets chart done" does not account for a second non-draft briefing after a reopen.
- `plugins/flow-next/docs/flowctl.md:1176` - contract table, `reopen` row: reads as if the next briefing is a no-op.
- `plugins/flow-next/skills/flow-next-chart/workflow.md:479-480` (Phase 4 briefing handoff) and `:502-507` (Phase 6 abandon/reopen) - both state the staling consequence without saying what the next `briefing` call now does. `:290` mentions "suggest briefing/capture when done".
- `plugins/flow-next/skills/flow-next-chart/SKILL.md:111` - flags table row for `briefing` / `--force`, checked against the new vocabulary.
- `plugins/flow-next/skills/flow-next-chart/references/examples.md` - add a worked reopen-then-rebrief example in the file's established shape (inferred operation / read-back point / evidence-consent boundary / terminal verdict). `CHART_VERDICT` grammar itself is unchanged - a re-finalized briefing still terminates `COMPLETE`.
- `plugins/flow-next/docs/architecture.md:88` (sidecar `briefings[]` row) and `:90` ("Immutable versioned briefing package... B1, B2") - clarify that a post-reopen re-brief advances the counter rather than reinstating a B-id.
- `GLOSSARY.md:24` - the `## Briefing package` term, "Draft or forced briefings are never silently capture-ready." Add the reopen case; keep the heading text (`test_glossary_terms` pins it).
- `CHANGELOG.md` - a new `## Unreleased` section above `## [flow-next 3.13.1]`. **No version bump, no `scripts/bump.sh`** (batched-release rule).

**Generated (never hand-edit):** `plugins/flow-next/codex/skills/flow-next-chart/*` regenerate via `./scripts/sync-codex.sh` run twice. `plugins/flow-next/docs/` has no codex counterpart.

**Tests:** extend `plugins/flow-next/tests/test_chart_docs_inventory.py` with an assertion pinning the discriminator's name and value set in `flowctl.md`, modelled on `test_envelope_error_classes_documented` (321-332). Consider adding the reopen invariant phrase to `ChartInvariantPhrases.test_skill_grounding_and_prototype` (347-367), the way `chart locate` and `local ledger` are pinned today.

`plugins/flow-next/templates/usage.md` + `.flow/usage.md`: the `## Chart` section is deliberately terse pipeline-summary prose; leave it unless the reopen nuance genuinely belongs at that altitude. If either is touched, **both** must change identically - `ChartUsageParity.test_template_and_dogfood_byte_identical` enforces byte-identity.

**Size:** M
**Files:** `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/architecture.md`, `plugins/flow-next/skills/flow-next-chart/{SKILL.md,workflow.md,references/examples.md}`, `GLOSSARY.md`, `CHANGELOG.md`, `plugins/flow-next/tests/test_chart_docs_inventory.py`, `plugins/flow-next/codex/**` (generated)

### Approach

- Match each file's existing register. `flowctl.md` contract-table rows are single terse sentences; `workflow.md` phases are numbered steps + bullet contracts; `examples.md` entries are four-row tables.
- CHANGELOG entries lead with the user outcome, then the changed journey, then mechanism - see `agent_docs/releasing.md` and the 3.13.0/3.13.1 entries as the shape.
- House style: plain hyphens, never em dashes.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/docs/flowctl.md:1095-1180` - envelope section and the chart contract table
- `plugins/flow-next/skills/flow-next-chart/workflow.md:451-510` - Phase 4 briefing handoff and Phase 6 abandon/reopen
- `plugins/flow-next/tests/test_chart_docs_inventory.py:321-332` - the assertion to model the new pin on
- `agent_docs/releasing.md` - CHANGELOG writing gate

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-chart/references/examples.md` - the four-row example shape
- `GLOSSARY.md:19-28` - the Briefing package term

### Acceptance
- [ ] Every stale claim listed above is corrected, in that file's register
- [ ] The discriminator's name and value set are documented in `docs/flowctl.md` alongside the envelope error classes (R9)
- [ ] `test_chart_docs_inventory.py` pins the discriminator name and values so code and docs cannot drift (R9)
- [ ] `references/examples.md` carries a worked reopen-then-rebrief example in the established shape
- [ ] `GLOSSARY.md` Briefing package term covers the reopen case; its heading text is unchanged
- [ ] `CHANGELOG.md` has an `## Unreleased` entry, user-outcome first; NO version bump and no `bump.sh` run
- [ ] `./scripts/sync-codex.sh` run twice, byte-idempotent, mirror diff committed
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` and `uvx ruff@0.16.0 check .`

## Acceptance
- [ ] All stale doc claims corrected across flowctl.md, chart skill, architecture.md, GLOSSARY.md
- [ ] Discriminator name + value set documented in flowctl.md and pinned by test_chart_docs_inventory
- [ ] Worked reopen-then-rebrief example added to references/examples.md
- [ ] CHANGELOG `## Unreleased` entry staged, no version bump
- [ ] sync-codex.sh run twice, byte-idempotent
- [ ] Full gate green (parallel suite + ruff)


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
