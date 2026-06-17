# fn-64-tracker-sync-project-flow-spec.6 Docs + GLOSSARY + CHANGELOG + version bump + codex mirror regen + flow-next.dev

## Description
### Goal
Land the docs, vocabulary, changelog, version bump, Codex mirror, and the flow-next.dev page in the same workstream. **Satisfies R11.**

### Investigation targets
- `plugins/flow-next/docs/tracker-sync.md` — new "Dependency projection" section parallel to the existing "Readiness projection" (~line 141): how `depends_on_epics` → blocked-by relations, per-adapter fidelity (Linear native / GitHub native-or-fenced), provenance, completed-blocker rule.
- `plugins/flow-next/docs/flowctl.md` (`flowctl sync` block ~726-753) — document `list-dep-relations` / `set-dep-relation` / `clear-dep-relation`.
- `plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md` — document the `<!-- flow:deps -->` fenced-block exclusion from divergence.
- `GLOSSARY.md` — add: **dependency projection**, **provenance ledger** (per-relation), **completed-blocker rule**. Follow the `## tracker` / `## Merge base` entry style.
- `CHANGELOG.md` — feature entry under the new version (`## [flow-next X.Y.Z] - YYYY-MM-DD`, bold lead phrase). Current version 2.0.0 → bump (feature). Run `scripts/bump.sh <new-version>` (touches all five manifest surfaces; do NOT hand-edit plugin.json siblings).
- `scripts/sync-codex.sh` — after the skill/reference edits from fn-64.2–.5 land, run `bash scripts/sync-codex.sh` to regen `plugins/flow-next/codex/skills/flow-next-tracker-sync` and commit the mirror (cp -R whole-tree; audit for any AskUserQuestion/Task rewrites — none expected here).
- flow-next.dev (`~/work/flow-next.dev`): `src/content/docs/teams/tracker-sync.mdx` (dependency-projection section), `src/content/docs/releases/changelog.mdx` (newest-at-top `## Latest` entry per `agent_docs/releasing.md` format), bump `src/lib/site.ts` `FLOW_NEXT_VERSION` + `package.json`. Run `pnpm build` gate. Commit separately in the flow-next.dev repo.

### Notes
Docs-last task; depends on the implementation (fn-64.1, fn-64.5) being settled so prose matches reality. Per CLAUDE.md this is NOT a docs-only PR (it ships with code), so the version bump IS required.
## Acceptance
- All listed docs updated + accurate against the shipped behavior; GLOSSARY terms added.
- CHANGELOG entry + `scripts/bump.sh` version bump applied across all manifests.
- Codex mirror regenerated + committed.
- flow-next.dev tracker-sync page + changelog updated, `FLOW_NEXT_VERSION`/`package.json` bumped, `pnpm build` green.
- Repo gate green: `bash plugins/flow-next/tests/ci_test.sh` (or the repo's documented gate).
## Done summary
Landed the fn-64 docs-last deliverables in the flow-next repo: new Dependency-projection section in docs/tracker-sync.md, the list/set/clear-dep-relation subcommands in docs/flowctl.md, three GLOSSARY terms (dependency projection, provenance ledger, completed-blocker rule), the 2.1.0 CHANGELOG feature entry, a minor version bump (2.0.0 → 2.1.0) across all manifests via scripts/bump.sh, and the regenerated Codex mirror of the tracker-sync references. impl-review (rp) returned SHIP with zero findings.
## Evidence
- Commits: 34de130056f52233addf958e24ed0c70725c3d21
- Tests: python3 -m unittest test_tracker_sync_state (30 passed), python3 -m unittest test_dogfood_template_parity test_template_canonical test_install_cursor_parity test_codex_delegation_gates (52 passed), python3 -m py_compile flowctl.py, bash scripts/sync-codex.sh validators green (via bump.sh)
- PRs: