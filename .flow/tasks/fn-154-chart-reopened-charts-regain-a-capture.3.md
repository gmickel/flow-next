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
- `plugins/flow-next/docs/README.md` § **Notable updates** - REQUIRED. This is a behavior-affecting change (a command that used to no-op now emits), and that section is the docs entry point for exactly those. One line, newest first, in the format documented inline in the section.
- `CHANGELOG.md` - a new `## Unreleased` section above `## [flow-next 3.13.1]`.

**Release-gate reconciliation (read before deciding).** `agent_docs/releasing.md` says to bump when `plugins/<plugin>/skills/**/*.md` change, and this task edits skill files. A narrower, later rule in the repo's committed root `CLAUDE.md` overrides it. Quoted verbatim from **`CLAUDE.md:101`** (section "Editing rules"), so this does not rest on an unverifiable claim:

> **Version bumps are batched, not per-spec.** When implementing a spec, land the code + docs + an `## Unreleased` CHANGELOG entry (repo + docs-site), but do NOT run `scripts/bump.sh` or touch the version manifests / `FLOW_NEXT_VERSION`. The release + version-number decision is made separately, later, across several accumulated specs - to avoid version churn. Spec/task acceptance that says "bump to X.Y.Z" means *stage under `## Unreleased`*; the actual bump happens at the batched release.

This task therefore **stages** the release under `## Unreleased` and performs **no** bump.

**The quoted clause says "repo + docs-site" - both halves are this task's deliverable.** The public docs site is a **separate checkout at `~/work/flow-next.dev`** (source of `https://flow-next.dev`), so it is a separate commit in a separate repository, not a file in this tree. It is still part of Definition of Done here, not a later cleanup:

- `~/work/flow-next.dev/src/content/docs/releases/changelog.mdx` - stage a `### Unreleased - <short title>` block at the top of `## Latest`, in that page's mandatory format (bold problem-first one-liner, then a `<details><summary>Detail</summary>` block). Note that this page currently has **no** Unreleased convention - every block is a shipped `### X.Y.Z`. Introducing one is the intended staging shape; the batched release later renames it to the real version number.
- **Do NOT** touch `src/lib/site.ts` `FLOW_NEXT_VERSION` or `package.json` - those are version surfaces and move only at the batched release, same rule as the repo manifests.
- **Landing-page notable-updates desk:** `agent_docs/releasing.md` calls for a homepage item on a behavior release. That desk shows one prominent latest update plus three preceding ones and is keyed to *shipped versions*, so it is updated at the batched release, not while staging. Record that decision here rather than leaving the surface silently unaddressed.
- Gate before handoff: `cd ~/work/flow-next.dev && pnpm build`.

If that checkout is absent on the machine running this task, do not silently skip it: report the docs-site entry as an outstanding release-staging deliverable in the task summary so the batched release picks it up. Verify the clause is still present before relying on it (`grep -n 'Version bumps are batched' CLAUDE.md`); if it has been removed, follow `agent_docs/releasing.md` and bump instead. Cite `CLAUDE.md:101` in the commit message so the next reader does not "fix" the missing bump.

**Generated (never hand-edit):** `plugins/flow-next/codex/skills/flow-next-chart/*` regenerate via `./scripts/sync-codex.sh` run twice. `plugins/flow-next/docs/` has no codex counterpart.

**Tests:** extend `plugins/flow-next/tests/test_chart_docs_inventory.py` with an assertion pinning `supersedes_stale` and its presence rule in `flowctl.md`, modelled on `test_envelope_error_classes_documented` (321-332). Consider adding the reopen invariant phrase to `ChartInvariantPhrases.test_skill_grounding_and_prototype` (347-367), the way `chart locate` and `local ledger` are pinned today.

`plugins/flow-next/templates/usage.md` + `.flow/usage.md`: the `## Chart` section is deliberately terse pipeline-summary prose; leave it unless the reopen nuance genuinely belongs at that altitude. If either is touched, **both** must change identically - `ChartUsageParity.test_template_and_dogfood_byte_identical` enforces byte-identity.

**Size:** M
**Files (this repo):** `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/README.md`, `plugins/flow-next/docs/architecture.md`, `plugins/flow-next/skills/flow-next-chart/{SKILL.md,workflow.md,references/examples.md}`, `GLOSSARY.md`, `CHANGELOG.md`, `plugins/flow-next/tests/test_chart_docs_inventory.py`, `plugins/flow-next/codex/**` (generated)
**Files (separate repo, separate commit):** `~/work/flow-next.dev/src/content/docs/releases/changelog.mdx`

### Approach

- Match each file's existing register. `flowctl.md` contract-table rows are single terse sentences; `workflow.md` phases are numbered steps + bullet contracts; `examples.md` entries are four-row tables.
- CHANGELOG entries lead with the user outcome, then the changed journey, then mechanism - see `agent_docs/releasing.md` and the 3.13.0/3.13.1 entries as the shape.
- House style: plain hyphens, never em dashes.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/docs/flowctl.md:1095-1180` - envelope section and the chart contract table
- `plugins/flow-next/skills/flow-next-chart/workflow.md:451-510` - Phase 4 briefing handoff and Phase 6 abandon/reopen
- `plugins/flow-next/tests/test_chart_docs_inventory.py:321-332` - the assertion to model the new pin on
- `agent_docs/releasing.md` - CHANGELOG writing gate, the docs-site changelog format + register rules, and the bump rule this task deliberately does not follow
- `CLAUDE.md:101` (repo root, "Editing rules") - the batching rule that overrides it, quoted in full above
- `plugins/flow-next/docs/README.md` § Notable updates - the format is documented inline in that section

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-chart/references/examples.md` - the four-row example shape
- `GLOSSARY.md:19-28` - the Briefing package term

### Acceptance
- [ ] Every stale claim listed above is corrected, in that file's register
- [ ] `supersedes_stale` (name, array-of-B-ID type, presence-only-when-superseding rule) is documented in `docs/flowctl.md` alongside the envelope error classes (R9)
- [ ] `test_chart_docs_inventory.py` pins `supersedes_stale` and its presence rule so code and docs cannot drift (R9)
- [ ] `references/examples.md` carries a worked reopen-then-rebrief example in the established shape
- [ ] `GLOSSARY.md` Briefing package term covers the reopen case; its heading text is unchanged
- [ ] `plugins/flow-next/docs/README.md` § Notable updates carries a newest-first line for this behavior change
- [ ] Docs-site staged (separate commit in `~/work/flow-next.dev`): `### Unreleased` block atop `## Latest` in `releases/changelog.mdx`, in that page's problem-first format; `FLOW_NEXT_VERSION` and `package.json` left untouched; `pnpm build` green. If the checkout is unavailable, the task summary names it as an outstanding release-staging deliverable
- [ ] The homepage notable-updates desk is explicitly deferred to the batched release (it is keyed to shipped versions), and that decision is recorded rather than left silent
- [ ] `CHANGELOG.md` has an `## Unreleased` entry, user-outcome first; NO version bump and no `bump.sh` run, per the `CLAUDE.md:101` batching rule, verified present and cited in the commit message
- [ ] `./scripts/sync-codex.sh` run twice, byte-idempotent, mirror diff committed
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` and `uvx ruff@0.16.0 check .`
## Acceptance
- [ ] All stale doc claims corrected across flowctl.md, chart skill, architecture.md, GLOSSARY.md
- [ ] `supersedes_stale` documented in flowctl.md and pinned by test_chart_docs_inventory
- [ ] Worked reopen-then-rebrief example added to references/examples.md
- [ ] docs/README.md Notable updates line added
- [ ] Docs-site `### Unreleased` block staged in ~/work/flow-next.dev (separate commit, pnpm build green, version surfaces untouched); homepage desk explicitly deferred to the batched release
- [ ] CHANGELOG `## Unreleased` entry staged, no version bump (`CLAUDE.md:101` batching rule verified present and cited in the commit message)
- [ ] sync-codex.sh run twice, byte-idempotent
- [ ] Full gate green (parallel suite + ruff)
## Done summary
Corrected every surface that said or implied the next `chart briefing` after a `chart reopen` is a no-op (flowctl.md envelope + command block + contract rows, chart SKILL/workflow/examples, architecture.md, GLOSSARY.md, docs/README.md Notable updates), documented `supersedes_stale` alongside the envelope error classes with its type and presence/absence rules, and pinned that contract in `test_chart_docs_inventory.py` scoped to the `### v1 JSON envelope` section so the docs cannot drift from the code. Per-briefing `status` is documented where it actually lives (the chart sidecar's `briefings[]`) - the spec's R3 claim that it is in `chart show --json` is wrong and no projection was added. Release staged under `## Unreleased` in CHANGELOG.md with no version bump per the CLAUDE.md:101 batching rule (verified present, cited in the commit); the flow-next.dev docs-site changelog is staged as a separate commit (1928831) in ~/work/flow-next.dev with `pnpm build` green and `FLOW_NEXT_VERSION`/`package.json` untouched; the homepage notable-updates desk is keyed to shipped versions and is deliberately deferred to the batched release.
## Evidence
- Commits: c733198166709a8d41af4d3f94ba615dc1c97a47, 9e54ab3b1457fe0b1c9c18bce68209f06f0a6f67, be30e74da277e962236267f8a561ec1e8ab78c54, 6bdde651b36c68d59e9b8fd5c91b18fc0c5f8b42
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing test_capture_chart_handoff test_chart_tracker_projection test_chart_docs_inventory -q (baseline: green, 113 tests), python3 scripts/run_tests_parallel.py (files=178 ran=3846 failures=0 errors=0), uvx ruff@0.16.0 check . (All checks passed), cd ~/work/flow-next.dev && pnpm build (80 pages, green), live CLI probe: chart create/resolve/briefing/reopen/briefing verified 'fn-1 briefing B2 status=final (supersedes stale B1)' and supersedes_stale=['B1','B2'] after a second reopen
- PRs: