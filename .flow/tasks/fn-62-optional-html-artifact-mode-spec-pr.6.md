---
satisfies: [R14]
---

## Description
Cut 2.0.0 — the FINAL task, after the docs-site tasks (.7/.8) per the release procedure (site changelog + version bump precede the tag): version lockstep, the documented crossEpic alias removal across ALL its surfaces, Codex mirror regen with a real audit, CHANGELOG.

**Size:** M
**Files:** CHANGELOG.md, plugins/flow-next/.claude-plugin/plugin.json, plugins/flow-next/.codex-plugin/plugin.json, plugins/flow-next/.cursor-plugin/plugin.json, .claude-plugin/marketplace.json, .agents/plugins/marketplace.json, plugins/flow-next/scripts/flowctl.py (crossEpic), plugins/flow-next/tests/test_config_alias.py, plugins/flow-next/skills/flow-next-setup/workflow.md (legacy-alias prose), agent_docs/releasing.md (surface-count claims), plugins/flow-next/docs/flowctl.md (alias row), .flow/config.json (stale persisted key in this repo), plugins/flow-next/codex/** (regen)

## Approach
- Follow agent_docs/releasing.md; `bump.sh major flow-next` covers the 5 version surfaces (3 plugin.json incl. .cursor — easy to miss — + 2 marketplace.json). Sweep descriptions/longDescription for stale counts (memory: skill-adding-version-bump-leaves-stale).
- Remove the `planSync.crossEpic` alias per the documented 1.x deprecation promise — ALL surfaces: flowctl.py (~:5123-5135 <!-- Updated by plan-sync: crossEpic mirror block drifted from :5114-5130 to ~:5123-5135 — confirm before editing -->, :1196), test_config_alias.py (convert to a removal regression test), flowctl.md alias row, flow-next-setup/workflow.md legacy-alias comments/footnotes, any releasing.md claims that undercount bump.sh's synced surfaces, AND this repo's own committed `.flow/config.json` (drop the stale persisted `planSync.crossEpic` key; keep/confirm the canonical `planSync.crossSpec` value). OWN breaking-change line in CHANGELOG — never folded silently into the bump.
- Regen Codex mirror (scripts/sync-codex.sh) AFTER fn-62.3/.4/.5 land; run a dedicated mirror audit (memory: mirror-regen-exposes-latent-canonical — fn-60's regen took 4 NEEDS_WORK rounds; budget for it): verify the references/ copy is byte-identical, no R2 ask-block injected into new/changed files, sentence-boundary check on any injected blocks, no surviving canonical tool names.
- CHANGELOG 2.0.0 entry: Added (HTML artifact mode, spec/PR lenses, lavish optional dep, artifacts.html config, .flow/artifacts/) / Removed (crossEpic alias — BREAKING) / Notes (opt-in, zero change when off).

## Investigation targets
**Required:**
- agent_docs/releasing.md — full release procedure incl. docs-site-before-tag ordering
- plugins/flow-next/scripts/flowctl.py:~5123-5135 + :1196 — alias code <!-- Updated by plan-sync: crossEpic mirror block now at ~:5123-5135 (was :5114-5130) -->
- plugins/flow-next/tests/test_config_alias.py — current alias test to convert
- .flow/config.json — stale persisted planSync.crossEpic in this repo
- scripts/sync-codex.sh — regen entry point
**Optional:**
- .flow/memory/bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11

## Acceptance
- [ ] All 5 version surfaces + CHANGELOG read 2.0.0; counts in descriptions verified current
- [ ] crossEpic alias removed from flowctl.py AND its prose surfaces (setup workflow, flowctl.md, releasing.md claims); removal regression test passes; CHANGELOG carries the explicit BREAKING line
- [ ] This repo's .flow/config.json no longer carries planSync.crossEpic; planSync.crossSpec confirmed canonical; flowctl config get planSync round-trips clean
- [ ] Mirror regenerated; audit checklist (byte-identical references copy, no spurious R2 blocks, no canonical tool names) recorded in the task summary
- [ ] Confirmed .7/.8 (docs-site incl. site changelog + FLOW_NEXT_VERSION) landed BEFORE the tag
- [ ] Full gate green (lint/typecheck/tests where applicable)

## Done summary
Cut the 2.0.0 release on the branch: bump.sh major synced all 5 version surfaces (3 plugin.json incl. .cursor + 2 marketplace.json) + README badge; removed the planSync.crossEpic config alias per the 1.x deprecation promise (alias map emptied, init pre-merge mirror removed, tests converted to removal regressions, prose surfaces + releasing.md surface-count claim fixed, repo .flow/config.json stale key dropped, dogfood flowctl re-synced byte-identical); regenerated + audited the Codex mirror (references/ byte-identical, diff limited to canonical prose edits, no spurious ask-blocks, validators green, idempotent re-sync); CHANGELOG 2.0.0 entry with its own BREAKING line. RP impl-review: SHIP (first pass, R14 met).

Mirror audit checklist (recorded per acceptance): references/ copy byte-identical (diff -r clean); mirror diff = exactly the 2 canonical prose edits (plan-sync.toml footnote + setup workflow crossEpic lines); no R2 ask-block injected into changed regions (footnote lands between complete sentences); token sweep clean (no AskUserQuestion/request_user_input/ToolSearch in skill prose); sync validators all green; second sync-codex.sh run byte-idempotent. Noted latent pre-existing (unchanged, on main since <=1.14.0): two `${PLUGIN_ROOT}/skills/...` template-diff refs in codex setup workflow escape the braced-form rewrite/validator — out of this task's scope.

Docs-site precondition confirmed: flow-next.dev commits 1dd356d (visual-aids + 2.0.0 changelog + FLOW_NEXT_VERSION=2.0.0) and 2a226be (pipeline page) are committed locally in ~/work/flow-next.dev (intentionally unpushed; go live with the release) — the "site changelog + version bump BEFORE the tag" ordering holds since the tag is cut post-merge.

POST-MERGE STEPS (deliberately NOT executed — this work ships via PR; human-owned merge rule): 1) merge the PR; 2) git tag flow-next-v2.0.0 && git push origin flow-next-v2.0.0 (triggers release + Discord); 3) push ~/work/flow-next.dev (commits 1dd356d, 2a226be); 4) re-run local installers to dogfood (install-codex.sh / install-cursor.sh).
## Evidence
- Commits: ee13019bed09fcc7ac2cbcc5c1a052666a26eed3
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (1070 tests OK, 2 skipped), python3 -m py_compile plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py, bash -n plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh, diff -r plugins/flow-next/references plugins/flow-next/codex/references (byte-identical), .flow/bin/flowctl config get planSync.crossSpec --json / planSync.crossEpic --raw --json (round-trip clean)
- PRs: