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
- **CHANGELOG:** create `## Unreleased` header above 2.7.2; `### Added` entry (bold lead-in + prose, house style) ending with an explicit `Downstream (at release):` line naming the flow-next.dev orchestration-page + skills/setup-page pointer edits (the tracked handoff artifact — R7). No version bump, no bump.sh (batched).
- **Tests (R8, all deterministic — prose-only review is NOT acceptable coverage):** new `plugins/flow-next/tests/test_model_routing_scaffold.py`:
  (a) template shape — exists, markers well-formed, ≤ budget line-count guard, every CLI-dependent route line carries a probe sentinel, no active codex/cursor reference outside sentinel lines;
  (b) probe composition — a reference implementation of the documented sentinel line transform, asserted for all four HAVE_CODEX×HAVE_CURSOR states (no active route to a failed-probe CLI; install notes present);
  (c) uninstall removal — pure text transform: well-formed → removed inclusive; 0/2 starts, 0/2 ends, out-of-order → untouched; PLUS prose-contract assertions on `commands/flow-next/uninstall.md` (both marker strings present, exactly-one/ordered rule stated, damaged→report-untouched stated, report line extended);
  (d) workflow prose contracts (smoke_test.sh, following the existing SKILL.md-Ralph-block prose-contract pattern) — headless-skip rule present, frozen option strings present, "never pre-set work.delegateConsent" present, scaffold processing ordered after the Docs block.
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
- [ ] CHANGELOG `## Unreleased` created with the entry + `Downstream (at release):` handoff line; no version bump
- [ ] New tests green: template shape + sentinel invariant, four-state probe composition, removal algorithm incl. damaged cases, workflow prose contracts; full pytest + smoke green
- [ ] Final sync-codex regen committed

## Done summary
Finalized fn-88: `/flow-next:uninstall` now removes the `<!-- flow-next:model-routing:start/end -->` scaffold block via the deterministic damaged-marker algorithm (exactly-one + ordered → remove inclusive; any other state → report + untouched), with the report line extended. Added the "in your repo" pointer to orchestration.md, the setup-row optional-scaffold clause to README + docs/skills.md (verbatim-matched pair), the troubleshooting uninstall note, and a `## Unreleased` CHANGELOG entry with a `Downstream (at release):` handoff line for the flow-next.dev pages. New deterministic test coverage (`test_model_routing_scaffold.py`) locks the template shape + probe-sentinel invariant, the four-state HAVE_CODEX×HAVE_CURSOR composition transform, the uninstall marker-removal algorithm incl. every damaged case + uninstall.md prose contract, and the setup workflow prose contract on canonical + Codex mirror; smoke_test.sh gained a matching workflow prose-contract block. Full pytest + smoke + sync-codex validation all green; no version bump (batched).
## Evidence
- Commits: c9e11d89dc590d7e11873ee12287749de4ae6cfe
- Tests: uvx pytest plugins/flow-next/tests -q (1455 passed, 2 skipped), bash plugins/flow-next/scripts/smoke_test.sh (143 passed, 0 failed; run from outside repo), ./scripts/sync-codex.sh (validation green)
- PRs: