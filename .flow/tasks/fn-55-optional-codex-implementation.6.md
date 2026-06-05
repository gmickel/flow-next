---
satisfies: [R10]
---

## Description
Ship the cross-platform mirror, docs, and version bump — the final integration task. Mirror the new reference + skill changes to the Codex mirror via `scripts/sync-codex.sh`, update every doc the feature touches, and bump the plugin version (skill change) including the **currently-stale Codex marketplace**. This is the last task in the chain; its impl-review must use the spec-wide merge base (memory: final-integration rule).

**Size:** M
**Files:** `scripts/sync-codex.sh`, `scripts/bump.sh`, `plugins/flow-next/commands/flow-next/work.md` (argument-hint), `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/docs/ralph.md`, `plugins/flow-next/docs/README.md`, `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `plugins/flow-next/skills/flow-next-setup/templates/usage.md`, `.flow/usage.md`, version files (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, both `plugin.json`)

## Approach
- **sync-codex.sh** (repo-root `scripts/sync-codex.sh` — NOT under `plugins/flow-next/scripts/`): the new `references/codex-delegation.md` mirrors automatically via the existing `cp -R` of the skill dir (`scripts/sync-codex.sh:133`). Verify the global `$FLOWCTL`/path rewrites + the `AskUserQuestion`→numbered-prompt and `Task`→`spawn_agent` passes cover the new file AND do NOT mangle the literal `codex exec` invocation the reference teaches (it's the thing being run, not a tool-name to rewrite). Add a targeted block only if the global passes miss it. Audit per memory `audit-sync-codexsh-during-planning-for-2026-04-30` + `sync-codexsh-tool-substitution-needs-2026-05-18`. <!-- Updated by plan-sync: fn-55.5 finished authoring `references/codex-delegation.md` (all stub sections now filled: pre-flight .2, invocation .3, classification/safety .4, circuit-breaker/ralph-guard/receipts/attribution .5). The Codex mirror copy at `plugins/flow-next/codex/skills/flow-next-work/references/codex-delegation.md` STILL carries the OLD stub header ("...sections are stubbed at the end of this file") — the sync regeneration is load-bearing, not cosmetic: it MUST overwrite that stale stub with the complete canonical file. Also re-mirror the fn-55.5 worker.md changes (Phase 2 delegation hook + HEAD/`.flow` integrity assertions + `DELEGATION_RESULT=`/`DELEGATION_ACTION=` terminal signal + `evidence.delegation` inline + `AI-Orchestrator`/`AI-Implementer` Phase 3 trailers) and the phases.md host circuit-breaker counter/bridge — sync-codex regenerates the whole skill+agent dirs, so verify `git status` shows the mirror's worker.md/phases.md updated, not just the reference. -->
- Note: the platform gate (R4 #1) disables delegation on non-Claude-Code orchestrators, so the mirrored reference is ship-and-disable on the Codex mirror by design.
- **bump.sh:** extend it to also bump `.agents/plugins/marketplace.json` (the Codex marketplace), which it currently does NOT touch — it is stale at `1.5.0` while the plugin is `1.6.0`. The fn-55 bump must bring it current AND keep it in sync going forward.
- **flowctl.md:** add the 6 `work.delegate*` config keys (follow the `tracker.perEvent.*` row format: key | type | default | description + precedence note + link to `codex-delegation.md`).
- **ralph.md:** add an autonomous-delegation section (mirror the tracker-sync section ~L568): delegation proceeds only when `work.delegateConsent=true` pre-set, no live `AskUserQuestion`, failures fall back without stalling, `yolo` blast-radius note, `REVIEW_MODE=none` verification backstop.
- **CLAUDE.md:** add a narrow carve-out line right after the "Do not spawn codex/copilot from inside flowctl" prohibition (~L29) — `/flow-next:work` delegation is host-orchestrated implementation-offload (not a judgment hand-off), recorded as the fn-55 decision; prevents a future agent reverting/blocking it.
- **commands/flow-next/work.md:** update the `argument-hint` frontmatter to include `[delegate:codex|delegate:local]` (the main user-facing activation surface) alongside the existing branch/review flags. Mirror to the Codex mirror via sync-codex.
- **README.md:** one row/note on the opt-in delegation surface (`delegate:codex` arg / `work.delegate=codex` config) near the `/flow-next:work` row, linking the flowctl config keys.
- **docs/README.md** index: add the `references/codex-delegation.md` row.
- **CHANGELOG.md:** `### Added` entry (opt-in codex delegation, gpt-5.5/medium default, progressive disclosure, Ralph-safe with pre-consent). <!-- Updated by plan-sync: fn-55.5 amended `ralph-guard.py` and bumped `RALPH_GUARD_VERSION` 0.14.0 → 0.15.0 — the CHANGELOG/ralph.md note should reflect the guard now allows the strict canonical `codex exec` delegation shape (the prior version blocked every delegation batch in Ralph mode). -->
- **.flow/usage.md + setup template** (parity — the parity guard test): one-line note under `/flow-next:work` on the opt-in mode. Keep both files identical.
- **Version bump:** `scripts/bump.sh minor flow-next` (skill change → minor); runs sync-codex + badge. GLOSSARY: no new term.
- **flow-next.dev (same-workstream, separate repo):** per CLAUDE.md, behavior/doc changes update `~/work/flow-next.dev` in the SAME workstream — it's a required deliverable, NOT deferred-to-maintainer (that applies only to the marketing site mickel.tech). Update the `/skills/work` page + the docs-site changelog (per `agent_docs/releasing.md` format, bump `src/lib/site.ts` `FLOW_NEXT_VERSION` + `package.json`), run `cd ~/work/flow-next.dev && pnpm build`, and commit separately in that repo.

## Investigation targets
**Required**:
- `scripts/sync-codex.sh:133-138` (cp -R), path-patch + flow-next-work blocks, AskUserQuestion rewrite — confirm coverage of the new reference + no mangling of `codex exec` <!-- Updated by plan-sync: the `cp -R` at :133-138 regenerates the WHOLE skills+agents dirs, so confirm coverage of three fn-55.5 surfaces, not just the reference: (1) `references/codex-delegation.md` — mirror copy is currently a STALE STUB and must be overwritten with the fully-authored canonical file; (2) `agents/worker.md` — Phase 2 delegation hook + HEAD/`.flow` assertions + `DELEGATION_*` signal + `evidence.delegation` + attribution trailers; (3) `skills/flow-next-work/phases.md` — host circuit-breaker counter/bridge. -->
- `scripts/bump.sh:10-67` — what it updates (`.claude-plugin/marketplace.json`, both `plugin.json`) and where to add `.agents/plugins/marketplace.json`
- `plugins/flow-next/docs/flowctl.md` — config-key table format (`tracker.perEvent.*` rows)
- `plugins/flow-next/docs/ralph.md` (~L568) — tracker-sync autonomous section to mirror
- `CLAUDE.md` (~L29) — the prohibition line to annotate
- `plugins/flow-next/tests/test_dogfood_template_parity.py` — the usage.md ↔ template parity guard
**Optional**:
- `agent_docs/releasing.md` — version-bump + docs-site changelog procedure

## Acceptance
- [ ] `bash scripts/sync-codex.sh` mirrors `references/codex-delegation.md` to the Codex mirror with `$FLOWCTL`/tool-name rewrites applied AND the literal `codex exec` invocation intact (not mangled); `git status` shows the mirror updated; codex-mirror smoke/parity checks pass.
- [ ] `scripts/bump.sh` updates `.agents/plugins/marketplace.json` alongside `.claude-plugin/marketplace.json` + both `plugin.json`; after the fn-55 bump all four are the same new version (the Codex marketplace is no longer stale).
- [ ] `commands/flow-next/work.md` `argument-hint` includes `[delegate:codex|delegate:local]` (canonical + Codex mirror).
- [ ] `flowctl.md` documents all 6 `work.delegate*` keys with defaults + precedence; `ralph.md` has the autonomous-delegation section; `CLAUDE.md` has the carve-out line; `README.md` + `docs/README.md` index updated.
- [ ] `CHANGELOG.md` has the `### Added` entry.
- [ ] `.flow/usage.md` and `plugins/flow-next/skills/flow-next-setup/templates/usage.md` both carry the delegation note and remain identical (parity guard green).
- [ ] Plugin version bumped (minor) across `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, and both `plugin.json`; README badge updated.
- [ ] Full gate green (lint/typecheck/tests including parity + codex-mirror smoke); `~/work/flow-next.dev` updated in the same workstream (work page + docs-site changelog + version bump, `pnpm build` green) and committed separately in that repo.

## Done summary
_(pending implementation)_

## Evidence
_(pending implementation)_
