---
satisfies: [R5, R6, R7, R8]
---
# fn-160-setup-speed-batched-plumbing-refresh.4 model-pins staleness gate + Codex ask regrouping + finalization sweep

## Description
Staleness-gate the model-pins ceremony, regroup the UNCONDITIONAL Codex-mirror prompts (scope per review round 1 — no compound-prompt protocol), and run the finalization sweep (CHANGELOG + remaining docs + full gate).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-setup/workflow.md` (6e gate; post-split core), per-platform references from .3 as needed, `plugins/flow-next/skills/flow-next-setup/references/model-pins.md`, `scripts/sync-codex.sh` (if regrouping needs a transform tweak), codex mirror (regen), `plugins/flow-next/tests/test_model_pin_ceremony_prose.py`, `CHANGELOG.md`, `agent_docs/setup-modes.md` (confirm/adjust refresh prose), `plugins/flow-next/docs/platforms.md` (host-visible wording check)

### Approach
- **R5 staleness gate:** extend the `MODELS_ASK` computation (workflow.md:705-712, post-split location) — `models.verifiedAt` parsing to a date within ~90 days → skip probes AND the ask, summary outcome `skipped (fresh — verified <date>)`. Absent, malformed, or future-dated → treat as absent, ceremony offered. Explicit user request forces the ceremony. Reuse `models.verifiedAt` — no new config key (fn-115 owns the stamp; the `flowctl status` ~90-day nudge is the window's wording anchor).
- **R6 regrouping (unconditional asks ONLY):** fold into one numbered prompt only the Step 4a SPEC.md offer and the usage.md overwrite ask, when both fire. NOT moved: the HTML artifacts-in-git follow-up (conditional on HTML=Yes — stays sequential), the Step 2b mode gate, model-pins propose, docs-overwrite asks (result-dependent). Grouped-abort precedence per the spec plan decision: abort acts as the earliest-step abort among grouped questions; later grouped answers discarded unprocessed; abort copy reflects pre-prompt state (abort-option memory lesson). Post-transform transcript fixtures: both answered, each abort position, skip, malformed replies. Honest target ~8 → ~5-6 blocking waits.
- **Parity evidence (this task's share):** re-run the question/option inventory after regrouping — the diff vs .3's baseline must show ONLY the approved grouping moves, no content change.
- **Finalization:** `## Unreleased` CHANGELOG entry (user-outcome-first: faster setup, one-command upgrades; machinery last) + flow-next.dev docs-site note staged per the downstream chain; verify agent_docs/setup-modes.md + docs/platforms.md wording; NO version bump (batched-release rule).
- Full gate: `python3 scripts/run_tests_parallel.py`, `uvx ruff@0.16.0 check .`, flowctl propagation (cp + rsync + gen_tracker_manifest), `./scripts/sync-codex.sh` twice.

### Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-setup/references/model-pins.md` — ceremony sections A-F
- workflow.md 6e gate (post-split location from .3)
- codex mirror `plugins/flow-next/codex/skills/flow-next-setup/workflow.md` — current serialized ask sites (grep "numbered")

**Optional:**
- `plugins/flow-next/tests/test_model_pin_ceremony_prose.py` — assertions to extend
- `agent_docs/releasing.md` — CHANGELOG entry rules

### Key context
- Depends on .3 (edits the split files; regrouping must not fight the split).
- Date math in skill bash must be portable (macOS `date -v` vs GNU `date -d`) — prefer a `flowctl`-side comparison if shell portability gets ugly (fits the plumbing split; still no new config key).
- Memory lesson: smoke the POST-transform mirror output for the regrouped prompt.

### Acceptance
- [ ] Re-run with fresh verifiedAt: zero live CLI probes, zero pins ask, distinct summary line; stale/absent/malformed/future → ceremony offered; forced request always runs it
- [ ] Grouped prompt covers exactly the two unconditional asks; abort precedence per spec; transcript fixtures (answers/aborts/skip/malformed) green against the regenerated mirror; ~8 → ~5-6 waits
- [ ] Inventory diff vs .3 baseline shows only the approved grouping moves
- [ ] CHANGELOG `## Unreleased` entry + docs-site note staged; setup-modes/platforms wording verified; no version bump
- [ ] Full suite + ruff + propagation green (final gate for the spec)
## Acceptance
- [ ] R5: staleness gate on live probes/ask, distinct outcome string, malformed/future = absent, forced request honored
- [ ] R6: unconditional-ask regrouping with defined abort precedence + transcript fixtures; conditional asks stay sequential
- [ ] R7 (final): inventory diff shows only approved grouping moves; all consent gates fire under same conditions
- [ ] R8: full gate, sync-codex idempotency, symlink fixtures (from .2) green, schema drift test untouched
## Done summary
Not built — superseded. fn-160 planned a copy-mode refresh fast path + setup_version stamp; the copy-less install model (#352/#353, 4.0.0) removed copy mode, setup-mode, and the setup_version field entirely, so there is nothing to refresh or stamp. Closed 2026-08-19 alongside issue #314.
## Evidence
- Commits:
- Tests:
- PRs: https://github.com/gmickel/flow-next/pull/352, https://github.com/gmickel/flow-next/pull/353