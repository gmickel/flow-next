---
satisfies: [R6, R7]
---
# fn-170-chart-notes-correction-path-notes.3 docs, skill prose, CHANGELOG + propagation

## Description
---
satisfies: [R6, R7]
---

### Description
Document the correction path everywhere it is taught, stage the CHANGELOG entry, and run the flowctl propagation chain.

**Size:** S
**Files:** `plugins/flow-next/docs/flowctl.md`, `plugins/flow-next/skills/flow-next-chart/workflow.md`, `plugins/flow-next/skills/flow-next-chart/SKILL.md`, `CHANGELOG.md`, `.flow/bin/flowctl.py`, `plugins/flow-next/codex/**`

### Approach
- `docs/flowctl.md` chart section (~1211-1330): add `notes_append` to the resolve `--sharpen-file` doc + contract table row; document `sharpen_file_unknown_key`; note briefing-status fix and that a post-final-briefing correction reaches artifacts only via `chart reopen` re-mint (include task 2's fingerprint-scope finding). Follow the existing bolded key-term callout pattern (see `alias_collision`).
- Chart skill: workflow.md sharpen block (~374, ~410, ~533) - teach: when a resolution disproves a grounding note, carry the dated correction in `notes_append` in the SAME resolve; unattended mode writes a correction only when the measured answer directly contradicts a specific note, never speculative. SKILL.md tool-table row for resolve updated.
- CHANGELOG: `## Unreleased` entry (user-outcome-first per agent_docs/releasing.md), credit @sn-furali (#292). No version bump (batched releases).
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`; `rsync -a --delete --exclude __pycache__ plugins/flow-next/scripts/flowctl_tracker/ .flow/bin/flowctl_tracker/`; `python3 scripts/gen_tracker_manifest.py`; `./scripts/sync-codex.sh` TWICE (idempotency) - commit mirror diff with the canonical change.
- Final gate: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` both green.

### Investigation targets
**Required:**
- `plugins/flow-next/docs/flowctl.md:1211-1330` - chart section patterns
- `plugins/flow-next/skills/flow-next-chart/workflow.md:370-420,530-540` - sharpen prose to extend

**Optional:**
- `agent_docs/releasing.md` - changelog register rules

### Acceptance
- [ ] flowctl.md documents notes_append + sharpen_file_unknown_key + briefing-status behavior (R7)
- [ ] Chart skill prose teaches the correction path incl. unattended rule (R7)
- [ ] CHANGELOG Unreleased entry credits the reporter (R7)
- [ ] Dual copy + tracker manifest + sync-codex twice; mirror diff committed (R7)
- [ ] Full suite + ruff green (R6 confirmation)

## Acceptance
- [ ] flowctl.md + chart skill prose updated
- [ ] CHANGELOG Unreleased entry with reporter credit
- [ ] dual-copy/manifest/sync-codex propagation done, full gate green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
