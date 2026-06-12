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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
