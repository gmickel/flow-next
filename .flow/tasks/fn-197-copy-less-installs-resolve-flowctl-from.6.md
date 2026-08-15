# fn-197-copy-less-installs-resolve-flowctl-from.6 Downstream sweep and release notes

## Description
**What:** Downstream sweep + release notes — walk the whole chain per `~/work/agent-instructions/downstream-properties.md`.

**Execution checklist:**
1. Read `~/work/agent-instructions/downstream-properties.md` first and walk every property it lists. Known targets:
   - **flow-next.dev**: install + setup + platforms pages — the copy-mode story comes out everywhere; setup page states the install-once / setup-once-per-repo / re-run-only-on-snippet-bump model; migration note (delete old `.flow/bin`, `.flow/templates/spec.md`, `.flow/usage.md` — nothing depends on them).
   - **Microsite + AI x SDLC guide**: any setup/install references updated to the one-mode story.
   - **Vault** (`~/work/GordonsVault`): update flow-next operational notes touching setup/copies.
2. Release-notes draft for the batched release this rides in (candidate: the flow-98 + fn-195 major), in the repo's docs-site format: user-facing framing is "install the plugin once — your repos need no copies; existing copies can simply be deleted". If `SNIPPET_SCHEMA_VERSION` bumped, the upgrade-actions block says so. No benchmark numbers, no speed claims, no external attribution (standing rule).
3. Remind Gordon at release time to re-run `install-cursor.sh` / `install-codex.sh` on his machines (standing release step) — after this spec that's the LAST per-machine action that affects repo behavior.
4. Post-release verification from the RELEASED artifacts (not the dev tree): tmp repo, `.flow/` data, no copies, natural prompt on all four harnesses (Claude Code, Cursor CLI or app, Grok, Codex) — each resolves flowctl from its install. Also one legacy-shaped repo (leftover `.flow/bin`): everything still works and `/flow-next:plan` shows the delete-me nudge.

**Touches:** external properties only (flow-next.dev repo, microsite, vault) + release-notes files per agent_docs/releasing.md
## Acceptance
- [ ] Every property in downstream-properties.md walked; flow-next.dev, microsite/guide, and vault carry the one-mode story with the delete-copies migration note.
- [ ] Release notes drafted in the docs-site format; upgrade-actions block covers the snippet bump if any; register/format gates pass; no speed claims or external attribution.
- [ ] Post-release verification: all four harnesses resolve flowctl from their installs in a copy-less tmp repo; a legacy-shaped repo still works and plan shows the nudge.
- [ ] Gordon reminded to re-run install-cursor.sh / install-codex.sh.
## Done summary
Walked every property in `~/work/agent-instructions/downstream-properties.md` for the copy-less-installs story and drafted the batched 4.0.0 release notes. All external edits are committed on unpushed branches named `fn-197-copy-less` (docs site + guide); vault notes edited in place; nothing published, nothing deployed.

### Per-property outcome

- **flow-next.dev** (`~/work/flow-next.dev`) - **staged on branch `fn-197-copy-less`, commit `f3509f5`, not pushed, not merged, not deployed.** Rewrote the one-mode story on `install.mdx` (caution box -> "plugin updates need no setup re-run", setup bullet list, Grok + Cursor resolution lines, optional-CLI PATH block, the whole `## Updating` section incl. per-host subsections), `skills/setup.mdx` (What it does, Cursor/Grok sections, Re-running, "Why scripts, not symlinks" -> "Coming from an older install", worked example, tips, next step), `reference/troubleshooting.mdx` (lead section replaced by "Updated the plugin - do I re-run setup?" + a new "I have `.flow/bin/` from an old install" section; Windows recovery path 1 is now delete-the-copy), `first-30-minutes.mdx` (mode question removed, `.flow/bin/flowctl` -> `flowctl` in all four command blocks), `introduction.mdx` + `strategy/architecture.mdx` (Grok copy-mode claims), `orchestration/index.mdx` (four copy-mode parentheticals), `specs/writing-specs.mdx` (4-tier cascade -> 3-tier), `releases/versioning.mdx` (`.flow/usage.md` -> `flowctl usage`). Zero `copy mode` / `plugin mode` / `setup-mode` strings remain outside the historical changelog page. Gate: `pnpm build` green (81 pages); new heading anchors verified in the built HTML (`#updated-the-plugin---do-i-re-run-setup`, `#i-have-flowbin-from-an-old-install`) and the one inbound link repointed.
- **GrowthFactors microsite** (`~/work/code-factory-package`) - **nothing to change.** Its published surfaces (`dist/*.html`, `spec/*.md`, overlays) carry methodology and autonomy narrative only; no install, setup, or flowctl-resolution content. (Its own `CLAUDE.md` uses `.flow/bin/flowctl` because that repo is itself a legacy-shaped flow-next consumer - a post-release cleanup on Gordon's repos, not a microsite content change. Noted in the checklist.)
- **AI x SDLC guide** (`~/work/AI-x-SDLC-Starter-Kit`) - **staged on branch `fn-197-copy-less`, commit `53a3807`, not pushed.** One copy-mode claim existed: `guides/model-routing.md` L145 said the bridge recipes ride "the installed `.flow/usage.md`"; now states they come from `flowctl usage`, resolved live from the plugin install. Swept `guides/`, `snippets/`, `resources/` for `.flow/bin`, copy/plugin mode, setup-mode, and setup-re-run advice - no other hit. (`guides/flow-next.md` L125's `delegate:codex` is flow-98 residue, not this spec's - see checklist.)
- **Obsidian vault** (`~/work/GordonsVault/Spaces/Projects/flow-next`) - **edited in place** (not git). `flow-next - Platforms & Install.md`: the "Setup modes: plugin vs copy (fn-121, 3.1.0)" section replaced by "One setup mode: copy-less installs (fn-197...)" documenting the 3-rung chain, what was deleted vs deliberately kept (protected-path lists, gate rules), the repurposed `PLUGIN_MODE_COPY_ARTIFACTS`, and the standing per-machine-installer consequence; Grok + Cursor rows corrected; the `init` self-heal bullet marked historical. `flow-next - Architecture.md`: `setup-mode` dropped from the command inventory, the env-fallback bullet replaced by the 3-rung resolution, the `setup_mode: copy` CI-gate phrasing generalized. `flow-next - Skills Catalog.md`: setup row carries the 4.0.0/fn-197 behavior. `flow-next - Release Timeline.md`: one staged-release beat for the 4.0.0 batch (all three specs, the deferral, where the draft and staged branches live).

### Release-notes draft

`~/work/flow-next.dev/RELEASE-DRAFT-4.0.0.md` (on the same unpushed branch; lives outside `src/` so it does not render as a page - `agent_docs/releasing.md` names no draft location, so per the conductor's instruction it sits alongside the page edits). Contains a paste-ready `### 4.0.0` docs-site changelog entry in the customer register (user outcome first, upgrade actions opening the details block, plain hyphens, no benchmark numbers, no speed claims, no external attribution) covering all three batched specs, plus the full release checklist.

`SNIPPET_SCHEMA_VERSION` did **not** bump (still `1`, last changed in fn-121), so the upgrade-actions block states plainly that nobody is forced to re-run `/flow-next:setup`; all three upgrade actions are optional cleanups (delete copies, re-scaffold routing if you used `delegate:codex`, delete inert config keys).

### Carried forward (in the draft's checklist, not done here)

- **Item 3 - installer re-runs (release step, flagged as not-optional this time).** Re-run `scripts/install-cursor.sh` and `scripts/install-codex.sh` per machine after the release lands. The local Cursor install on this machine was refreshed mid-spec during fn-197.1's live probe and currently carries **unreleased** prose - it must be re-run from the released tag.
- **Item 4 - post-release verification.** Cannot run now; it must run against released artifacts (fresh tmp repo, four harnesses reporting a plugin-install flowctl path, plus one legacy-shaped repo showing the plan nudge). Written into the checklist verbatim.
- **flow-98 / fn-195 docs-site page rewrites are OUTSTANDING.** Both specs explicitly deferred their docs-site work to "release-time downstream"; this task's acceptance covers the copy-mode story only, so the pages that still describe removed delegation and the retired role map were inventoried (file + approximate line) in the checklist rather than rewritten here: `orchestration/index.mdx`, `skills/work.mdx`, `subagents/execution.mdx`, `cookbook.mdx`, `strategy/running-lean.mdx`, `flowctl/configuration.mdx`, plus a missing reach page and the four tier terms in the glossary. They must land before the site is published at 4.0.0.
- Gordon's own consumer repos (e.g. `~/work/code-factory-package`) still carry `.flow/bin` copies - post-release cleanup, harmless meanwhile via the rung-3 backstop.

Baseline: green (full suite + ruff green before any edit, per the conductor; re-verified after). No changes to the flow-next repo itself - `gate classify` reports an empty diff, so the full gate was run fail-closed and a green receipt written at `16522160`.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)


Host review (out-of-band: in-repo diff empty, no reservable artifact - reviewer claude-fable-5, fresh read-only subagent over the staged external branches + vault): SHIP with 5 findings; F1/F2/F4 (quickstart bare-flowctl claim, missing Windows best-effort hedge, unresolvable PATH placeholder) fixed on the staged branch as b0e30ab; F3/F5 added to the release-draft checklist. Safety verified: nothing pushed, main untouched in both external repos, no premature 4.0.0 language in src/.

stage: impl-review - ran (host backend, out-of-band over external staging; SHIP; fixes b0e30ab on the staged branch)
stage: post-release-verify - skipped(policy: release deferred; runs from released artifacts at 4.0.0)
stage: plan-sync - skipped(empty: no downstream todo tasks)
## Evidence
- Commits:
- Tests: python3 scripts/run_tests_parallel.py (files=189 ran=4368 failures=0 errors=0 skipped=8, suite_rc=0), uvx ruff@0.16.0 check . (All checks passed), cd ~/work/flow-next.dev && pnpm build (81 pages, exit 0), green receipt: .flow/tmp/green-receipts/16522160-unittest.json, impl-review: host backend SHIP (out-of-band over external staging - in-repo diff empty; reviewer claude-fable-5; safety-verified nothing pushed; staged-branch fixes b0e30ab)
- PRs: