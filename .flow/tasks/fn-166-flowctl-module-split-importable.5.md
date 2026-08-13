---
satisfies: [R4, R5]
---
# fn-166-flowctl-module-split-importable.5 Docs, CHANGELOG Unreleased + full final gate

## Description
Land every remaining doc surface, the CHANGELOG Unreleased entry, and run the full final gate for the spec.

**Size:** M
**Files:** root `CLAUDE.md` (final-gate propagation paragraph), `agent_docs/local-dev.md`, `plugins/flow-next/docs/flowctl.md` (`.flow/bin` tree at :38-42; :125 already rewritten in task .2), `plugins/flow-next/docs/architecture.md` (~:122-145 review-bookkeeping section), `plugins/flow-next/docs/memory-schema.md:158-163`, `agent_docs/optimizing-skills.md:25`, `plugins/flow-next/docs/platforms.md` (:209, :343 check), `CHANGELOG.md`

### Approach
- CLAUDE.md: extend the "When a change touches `flowctl.py` or `flowctl_tracker/`" paragraph — add `flowctl_review/` rsync, the entry-file copy (if task .2 added one), and the (generalized) manifest command.
- local-dev.md: propagation + integrity verification recipe for the new package (pattern-match the tracker recipe).
- architecture.md review-bookkeeping section: point to where the logic now lives (`flowctl_review/`) and confirm the write-ordering guarantees prose still holds with the unified verdict helper.
- memory-schema.md:158-163: widen "two flowctl copies in lockstep" to the full set (flowctl.py + entry file + flowctl_tracker/ + flowctl_review/).
- optimizing-skills.md:25: fix the stale "~24k-LOC single file" characterization.
- platforms.md: check the Codex-host install copy lines (:209 `cp "$CODEX_BIN/flowctl.py" .flow/bin/`, :343 "thin launcher") need the package/entry additions.
- CHANGELOG.md: NEW `## Unreleased` heading (3.15.0 is already released — do not append to it). Outcome-first: startup >=2x with measured numbers + parity-surface reduction; machinery last. Note the one-time line-anchor churn (open specs fn-158/fn-160 re-grep their flowctl.py anchors). NO version bump (batched releases per CLAUDE.md).
- FINAL GATE: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` + full propagation (cp flowctl.py, rsync BOTH packages, manifest generator(s), `./scripts/sync-codex.sh` TWICE with no diff on the second run). After the spec lands, run `/flow-next:sync` (plan-sync) for the anchor churn — note this in the PR body.

### Investigation targets
**Required** (read before coding):
- root `CLAUDE.md` — propagation paragraph ("When a change touches flowctl.py...")
- `plugins/flow-next/docs/architecture.md:115-150` — review bookkeeping / write-ordering section
- `CHANGELOG.md:1-40` — entry shape + confirm 3.15.0 is the released head

**Optional** (reference as needed):
- `agent_docs/releasing.md` — changelog ordering rules + rejection test
- `plugins/flow-next/docs/memory-schema.md:150-170` — lockstep contract prose

### Key context
- Both changelogs are user-facing release surfaces; write user-outcome-first, machinery last (agent_docs/releasing.md has the rejection test).
- Docs-only edits do NOT bump the plugin version; this whole spec stages under `## Unreleased`.

## Acceptance
- [ ] All listed docs updated; flowctl.md tree shows the new `.flow/bin` layout
- [ ] CHANGELOG `## Unreleased` entry, outcome-first with measured startup numbers; no version bump
- [ ] CLAUDE.md propagation command names every artifact in the new set (flowctl.py, entry file if any, both packages, manifest command)
- [ ] Full suite green: `python3 scripts/run_tests_parallel.py`; `uvx ruff@0.16.0 check .` clean
- [ ] `./scripts/sync-codex.sh` run twice; second run produces no diff
- [ ] `test_prompt_text_pinned` hashes unchanged across the whole spec diff

## Done summary
NOT IMPLEMENTED — closed as superseded, 2026-08-13.

This task's work moved in the fn-166 split: launcher + verdict-map work to `fn-190-flowctl-startup-importable-entry-for`, package extraction + distribution integrity to `fn-191-flowctl-review-terminal-machinery`. No code, docs, or tests were produced here; `done` is a lifecycle marker so the parent spec could be closed (`spec close` requires done tasks and flowctl has no supersede terminal). Read the successors.
## Evidence
- Commits:
- Tests:
- PRs: