---
satisfies: [R6, R7, R8]
---

## Description

Finalization: uninstall marker removal, test coverage, remaining doc pointers, CHANGELOG Unreleased entry, final mirror regen.

**Size:** M
**Files:** `plugins/flow-next/commands/flow-next/uninstall.md`, `plugins/flow-next/docs/troubleshooting.md`, `plugins/flow-next/docs/orchestration.md` ("in your repo" pointer), `README.md` + `plugins/flow-next/docs/skills.md` (setup row, keep verbatim-matched), `CHANGELOG.md`, `plugins/flow-next/tests/` (new test file), `plugins/flow-next/scripts/smoke_test.sh` (if smoke coverage fits), `plugins/flow-next/codex/**`

## Approach

- **Uninstall** (`commands/flow-next/uninstall.md:46-50`): add a paragraph removing the `<!-- flow-next:model-routing:start/end -->` block with the deterministic damaged-marker algorithm (exactly one start AND one end AND ordered → remove inclusive; else report + leave untouched — R6/R14 of spec). Extend the "Cleaned up" report line.
- **Docs:** `docs/troubleshooting.md` Uninstall section (~L140-149) lists the second marker block; `docs/orchestration.md` gains the "in your repo" pointer (usage.md section + setup ceremony) near "What stays fixed"; `README.md:303` + `docs/skills.md:44` setup one-liner gains the optional-scaffold clause — the two strings must match verbatim (existing pattern).
- **CHANGELOG:** create `## Unreleased` header above 2.7.2; `### Added` entry (bold lead-in + prose, house style). No version bump, no bump.sh (batched).
- **Tests (R8):** new `plugins/flow-next/tests/test_model_routing_scaffold.py` (or similar): template exists + markers well-formed + ≤ budget line-count guard; damaged-marker algorithm cases (0/2 starts, out-of-order → untouched; well-formed → removed) — test the removal logic as a pure text transform; probe-annotation shape (CLI-dependent lines individually comment-able). Ceremony default-skip is skill-prose — cover via smoke_test.sh only if a cheap deterministic probe exists; otherwise document as prose-reviewed (do not build an LLM-in-the-loop test).
- **Final regen:** `./scripts/sync-codex.sh` on the merged state; full gate.
- flow-next.dev pointer edits land in that repo at ship time (R7 downstream half — not files of this task; note in the summary for the maintainer walk).

## Investigation targets

**Required:**
- `plugins/flow-next/commands/flow-next/uninstall.md:40-63` — existing marker-removal paragraph + report block
- `plugins/flow-next/docs/troubleshooting.md:135-155` — uninstall docs shape
- `CHANGELOG.md:1-10` — entry style (2.7.2/2.7.1 entries)

**Optional:**
- `plugins/flow-next/tests/test_dogfood_template_parity.py` — test file conventions
- `plugins/flow-next/tests/test_template_canonical.py` — template-assertion test shape

## Key context

- Fence-aware parity (memory, binding): marker operations are line-based and must not care about fenced content inside the block (the block contains a markdown table).
- README + docs/skills.md setup rows are duplicated strings kept verbatim-identical — change both or neither.

## Acceptance

- [ ] Uninstall removes a well-formed block; damaged states (missing/duplicate/out-of-order markers) → report + untouched; report line extended
- [ ] troubleshooting.md + orchestration.md pointer + README/docs-skills.md rows (verbatim pair) updated
- [ ] CHANGELOG `## Unreleased` created with the entry; no version bump
- [ ] New tests green (markers, budget guard, removal algorithm, annotation shape); full pytest + smoke green
- [ ] Final sync-codex regen committed

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
