---
satisfies: [R5, R6, R7, R8]
---
# fn-160-setup-speed-batched-plumbing-refresh.4 model-pins staleness gate + Codex ask regrouping + finalization sweep

## Description
Staleness-gate the model-pins ceremony, regroup Codex-mirror blocking prompts, and run the finalization sweep (CHANGELOG + remaining docs + full gate).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-setup/workflow.md` (6e gate), `plugins/flow-next/skills/flow-next-setup/references/model-pins.md`, `scripts/sync-codex.sh` (if regrouping needs a transform tweak), codex mirror (regen), `plugins/flow-next/tests/test_model_pin_ceremony_prose.py`, `CHANGELOG.md`, `agent_docs/setup-modes.md` (confirm/adjust refresh prose), `plugins/flow-next/docs/platforms.md` (host-visible wording check)

### Approach
- **R5 staleness gate:** extend the `MODELS_ASK` computation (workflow.md:705-712, post-split location) — when `models.verifiedAt` parses to a date within ~90 days, skip probes AND the ask with summary outcome `skipped (fresh — verified <date>)`. Absent, malformed, or future-dated values → treat as absent, ceremony offered (existing behavior). An explicit user request in the invocation forces the ceremony. Reuse `models.verifiedAt` — no new config key (fn-115 owns the stamp; the `flowctl status` ~90-day nudge stays the wording anchor for the window).
- **R6 regrouping:** in the canonical prose + mirror, fold into the grouped 6d prompt the asks whose inputs are known before 6d fires and whose answers nothing before Step 7 consumes: the Step 4a SPEC.md offer, the usage.md overwrite ask, and the HTML-artifacts follow-up (present it conditionally within the group). NOT movable: the Step 2b mode gate (everything downstream branches on it), the model-pins propose (depends on post-6d probe results), docs-overwrite asks (depend on setup-block results). Target: fresh Codex copy-mode run drops from ~8 blocking waits to ~4; every question's content intact.
- **Finalization:** `## Unreleased` CHANGELOG entry (user-outcome-first: faster setup, one-command upgrades; machinery last) + flow-next.dev docs-site note staged per the downstream chain; verify agent_docs/setup-modes.md + docs/platforms.md wording still matches; NO version bump (batched-release rule).
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
- Memory lesson: smoke the POST-transform mirror output for the regrouped prompt (composed transforms only visible after regen).

### Acceptance
- [ ] Re-run with fresh verifiedAt: zero live CLI probes, zero pins ask, distinct summary line; stale/absent/malformed/future → ceremony offered; forced request always runs it
- [ ] Codex mirror fresh-run blocking waits measurably reduced (~8 → ~4) with all question content intact; mirror regenerated twice, guards green
- [ ] CHANGELOG `## Unreleased` entry (repo) + docs-site note staged; setup-modes/platforms wording verified; no version bump
- [ ] Full suite + ruff + propagation green (final gate for the spec)

## Acceptance
- [ ] R5: staleness gate on live probes/ask, distinct outcome string, malformed/future = absent
- [ ] R6: Codex blocking round-trips reduced by regrouping, no content dropped
- [ ] R7 (final): all asks + consent gates fire under same conditions
- [ ] R8: full gate, sync-codex idempotency, schema drift test untouched


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
