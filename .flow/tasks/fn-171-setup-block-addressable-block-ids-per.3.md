---
satisfies: [R7]
---
# fn-171-setup-block-addressable-block-ids-per.3 docs, CHANGELOG + propagation

## Description
---
satisfies: [R7]
---

### Description
Document `--id`, the nested state, and the CI check recipe; stage the CHANGELOG entry; run the propagation chain.

**Size:** S
**Files:** `plugins/flow-next/docs/flowctl.md`, `agent_docs/setup-modes.md`, `CHANGELOG.md`, `.flow/bin/flowctl.py`, `plugins/flow-next/codex/**`

### Approach
- `docs/flowctl.md` setup-block section (152-165): `--id` on all three verbs, default-unchanged note, nested per-(path,id) state, `check` with the exit-code table and a copy-mode CI recipe (non-zero on drift, no jq needed; --json for detail).
- `agent_docs/setup-modes.md` invariants: REWRITE invariant 2 itself ("Setup-block markers are EXACT strings... Never parameterize the marker") to: markers are derived deterministically from the block id; the default id yields the historical exact strings; free-form marker overrides remain forbidden. Plus the per-(path,id) keying note, following the numbered bolded-lead-sentence pattern. Never leave the old never-parameterize sentence standing beside the new feature.
- `plugins/flow-next/skills/flow-next-setup/workflow.md`: meta.json shape reference at ~line 823 updated to the nested form (call sites unchanged - default id).
- CHANGELOG `## Unreleased` (user-outcome-first per agent_docs/releasing.md), credit @sn-furali (#294). No version bump (batched releases).
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`; `rsync -a --delete --exclude __pycache__ plugins/flow-next/scripts/flowctl_tracker/ .flow/bin/flowctl_tracker/`; `python3 scripts/gen_tracker_manifest.py`; `./scripts/sync-codex.sh` TWICE; commit mirror diff with canonical change.
- Final gate: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` green.

### Investigation targets
**Required:**
- `plugins/flow-next/docs/flowctl.md:152-165` - section to extend
- `agent_docs/setup-modes.md` - invariants pattern

**Optional:**
- `agent_docs/releasing.md` - changelog register

### Acceptance
- [ ] flowctl.md documents --id, nested state, check + exit codes + CI recipe (R7)
- [ ] setup-modes.md invariant 2 rewritten (id-derived markers; default id = historical strings; free-form overrides still forbidden) + per-(path,id) note (R7)
- [ ] setup skill meta.json shape reference updated (R7)
- [ ] CHANGELOG Unreleased entry credits the reporter (R7)
- [ ] Dual copy + manifest + sync-codex twice; full gate green (R7)

## Acceptance
- [ ] flowctl.md + setup-modes.md + setup skill shape note updated
- [ ] CHANGELOG Unreleased entry with reporter credit
- [ ] propagation chain done, full gate green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
