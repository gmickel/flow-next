---
satisfies: [R2, R3, R4, R5, R8]
---

## Description

Wire the shipping win into the worker, apply the CROSS_SPEC caller fix, and REMOVE the shelved skip-gate machinery from the shipped CLI. The gate was proven non-viable (fn-83.6 verdict FAIL; decision record `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`) — this task makes the shipped surface reflect only what ships. Depends on fn-83.3 (anchor).

**Size:** M
**Files:** `plugins/flow-next/agents/worker.md` (anchor call + delete PLAN_DEVIATION line), `plugins/flow-next/skills/flow-next-work/phases.md` (CROSS_SPEC + delete PLAN_DEVIATION parser prose), `plugins/flow-next/scripts/flowctl.py` (+ `.flow/bin/flowctl.py` dogfood copy), `plugins/flow-next/tests/` (delete 3 test files), `optimization/plan-sync-gate/README.md` + `optimization/worker-anchor/README.md` (archive note), regenerated + committed mirror

## Approach

- **SURGICAL removal first (do this before wiring, verify tests green after):** delete from `plugins/flow-next/scripts/flowctl.py` — `cmd_plan_sync_probe` + its argparse registration, the probe-specific `_psp_*` helpers, `PLANSYNC_GATE_LEDGER` + the ledger writer, and the `planSync.gate` key from `get_default_config()`. **CRITICAL: `flowctl anchor` (fn-83.3) reuses `_psp_run_git` — KEEP that one helper** (relocate/rename to an anchor-neutral name if it reads cleaner; grep `cmd_anchor`/anchor helpers for every `_psp_*` they call and preserve exactly those). Delete tests `test_plan_sync_probe.py`, `test_plansync_gate_config.py`, `test_plan_sync_gate_corpus.py`. Re-sync the `.flow/bin/flowctl.py` dogfood copy (dual-copy byte-identical invariant). Confirm `test_anchor_bundle.py` + full suite green after removal. Two grep guards prove the removal (R4): user-surface `grep -rn 'plan.sync.probe\|planSync.gate\|plansync-gate' plugins/flow-next/{scripts,skills,agents}` clean, AND symbol-level `grep -n 'cmd_plan_sync_probe\|PLANSYNC_GATE_LEDGER\|_psp_' plugins/flow-next/scripts/flowctl.py` returning ONLY `_psp_run_git`.
- **worker.md (R2):** Phase 1 uses the single `flowctl anchor <TASK_ID> --md` call in place of the discrete show/cat/git/memory/glossary reads; explicit floor-not-ceiling prose (memory keyword-search + read-more freedom retained; Investigation-targets/Design-context reads in Phase 1.5 unchanged). **DELETE the existing `PLAN_DEVIATION` surface** — already in the tree from the pre-streamline gate work: the terminal line in worker.md (~:430) AND the prefix-anchored parser prose in phases.md (~:285). Both go (dead gate signal — nothing consumes it once the probe is removed). **Do NOT touch `BASE_COMMIT`** — it scopes the impl-review diff (Phase 4), anchors delegation rollback (Phase 2), and records commit-range provenance in done evidence (Phase 5), all independent of the gate and load-bearing; removing `base_commit` would break impl-review/delegation. Only the removed probe consumed `evidence.base_commit`.
- **CROSS_SPEC fix (R3):** phases.md plan-sync spawn prompt gains `CROSS_SPEC: <planSync.crossSpec value>` (single config-leaf read). Plan-sync spawn stays UNCONDITIONAL — no gate branch, no probe call, no mode matrix, no per-task gate slot. The CROSS_SPEC line is the only 3e change.
- **Archive note (R5):** `optimization/plan-sync-gate/README.md` — prepend a boxed ARCHIVED banner AND neutralize the active-voice framing in the body so it never reads as runnable ship guidance: any "merge gate", "ship gate", live-miss-loop, `planSync.gate`, or "residual for the PR" language is rewritten to past tense / "(historical — the gate did not ship)" or struck. Banner: "ARCHIVED — the plan-sync skip-gate this harness validated was proven non-viable and removed from the shipped CLI (fn-83.4); see `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`. Kept as the evidence behind that decision; nothing here is a runnable ship instruction." `optimization/worker-anchor/README.md` stays LIVE (its eval backs the shipped bundle) — note: "This eval backs the shipped `flowctl anchor` command."
- **Mirror (R8 mirror half):** single `sync-codex.sh` regen + commit with this task's canonical edits (parity green; anchor call intact in mirror); fn-83.5 re-runs as idempotency check.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py` — `cmd_plan_sync_probe`/`_psp_*`/`PLANSYNC_GATE_LEDGER`/`planSync.gate` (remove) AND `cmd_anchor` (find which `_psp_*` it calls — preserve those)
- `plugins/flow-next/agents/worker.md:21-111` — Phase 1 reads to replace with the anchor call
- `plugins/flow-next/skills/flow-next-work/phases.md` plan-sync spawn block — CROSS_SPEC insertion point (spawn stays unconditional)
- `plugins/flow-next/tests/test_anchor_bundle.py` — must stay green after removal

## Key context

The decision record is already committed (written during the streamline). This task must not leave any `plan-sync-probe`/`planSync.gate`/`plansync-gate.jsonl` reference in the shipped plugin (`grep -rn 'plan.sync.probe\|planSync.gate\|plansync-gate' plugins/flow-next/{scripts,skills,agents}` clean, allowing only the mirror which regenerates from canonical). Ralph/autonomous: unchanged — plan-sync spawn stays unconditional; no new receipts/prompts.

## Acceptance

- [ ] Probe/gate/ledger/config removed from flowctl.py + dogfood copy; 3 tests deleted; `_psp_run_git` (or its anchor-used helpers) preserved; `flowctl anchor` + full suite green
- [ ] both grep guards clean: `plan.sync.probe|planSync.gate|plansync-gate` in scripts/skills/agents; AND `cmd_plan_sync_probe|PLANSYNC_GATE_LEDGER|_psp_` in flowctl.py returns only `_psp_run_git`
- [ ] worker.md Phase 1 = single anchor call + floor prose; `PLAN_DEVIATION` line (worker.md) + parser prose (phases.md) DELETED (`grep -rn PLAN_DEVIATION plugins/flow-next/{agents,skills}` clean); `BASE_COMMIT` + evidence recording untouched (impl-review/delegation/provenance intact)
- [ ] `test_anchor_bundle.py` still validates the bundle against the discrete-read baseline (rename comments to "required anchor payload / legacy discrete-read baseline" so a future edit can't collapse it to merely checking `anchor` runs)
- [ ] CROSS_SPEC passed to every plan-sync spawn; spawn otherwise unconditional + byte-unchanged
- [ ] plan-sync-gate README ARCHIVED-banner + active-voice/`merge gate`/`planSync.gate` language neutralized to historical; worker-anchor README notes it backs the shipped anchor
- [ ] mirror regenerated + committed, parity green; smoke + full unittest green; no version bump

## Done summary
Wired the surviving fn-83 wins and removed the shelved skip-gate: worker.md Phase 1 now runs the single `flowctl anchor <TASK_ID> --md` call (floor-not-ceiling; BASE_COMMIT captured at Phase-1 end; done evidence records base_commit + the full base..HEAD commit list), phases.md 3e passes CROSS_SPEC to the still-unconditional plan-sync spawn (latent caller-bug fix), and the plan-sync-probe + gate ledger + planSync.gate config + 3 gate tests were surgically removed from the shipped CLI (`_psp_run_git` retained for anchor; dogfood copy re-synced byte-identical; both R4 grep guards now locked by test_worker_anchor_prose.py alongside a done-evidence provenance fixture). Optimization READMEs carry the ARCHIVED/live-evidence notes; Codex mirror regenerated and committed; rp impl-review SHIP (first pass, zero findings).
## Evidence
- Commits: 54c597af3ad88bdd928dac54193c6e0ec033d1d9
- Tests: uv run --with pytest python -m pytest plugins/flow-next/tests/ -q (1433 passed, 2 skipped, 188 subtests), (cd $(mktemp -d) && bash plugins/flow-next/scripts/smoke_test.sh) (138 passed, 0 failed), python3 -m unittest discover -s plugins/flow-next/tests -p test_worker_anchor_prose.py (9 passed), python3 -m unittest discover -s plugins/flow-next/tests -p test_anchor_bundle.py (21 passed), bash scripts/sync-codex.sh (parity guards green)
- PRs: