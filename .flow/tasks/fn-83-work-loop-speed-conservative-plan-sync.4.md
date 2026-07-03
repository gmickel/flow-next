---
satisfies: [R2, R3, R4, R5, R8]
---

## Description

Wire the shipping win into the worker, apply the CROSS_SPEC caller fix, and REMOVE the shelved skip-gate machinery from the shipped CLI. The gate was proven non-viable (fn-83.6 verdict FAIL; decision record `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`) — this task makes the shipped surface reflect only what ships. Depends on fn-83.3 (anchor).

**Size:** M
**Files:** `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/scripts/flowctl.py` (+ `.flow/bin/flowctl.py` dogfood copy), `plugins/flow-next/tests/` (delete 3 test files), `optimization/plan-sync-gate/README.md` + `optimization/worker-anchor/README.md` (archive note), regenerated + committed mirror

## Approach

- **SURGICAL removal first (do this before wiring, verify tests green after):** delete from `plugins/flow-next/scripts/flowctl.py` — `cmd_plan_sync_probe` + its argparse registration, the probe-specific `_psp_*` helpers, `PLANSYNC_GATE_LEDGER` + the ledger writer, and the `planSync.gate` key from `get_default_config()`. **CRITICAL: `flowctl anchor` (fn-83.3) reuses `_psp_run_git` — KEEP that one helper** (relocate/rename to an anchor-neutral name if it reads cleaner; grep `cmd_anchor`/anchor helpers for every `_psp_*` they call and preserve exactly those). Delete tests `test_plan_sync_probe.py`, `test_plansync_gate_config.py`, `test_plan_sync_gate_corpus.py`. Re-sync the `.flow/bin/flowctl.py` dogfood copy (dual-copy byte-identical invariant). Confirm `test_anchor_bundle.py` + full suite green after removal.
- **worker.md (R2):** Phase 1 uses the single `flowctl anchor <TASK_ID> --md` call in place of the discrete show/cat/git/memory/glossary reads; explicit floor-not-ceiling prose (memory keyword-search + read-more freedom retained; Investigation-targets/Design-context reads in Phase 1.5 unchanged). Do NOT add a `PLAN_DEVIATION` line (the probe that consumed it is gone). Do NOT change the evidence/`base_commit` schema.
- **CROSS_SPEC fix (R3):** phases.md plan-sync spawn prompt gains `CROSS_SPEC: <planSync.crossSpec value>` (single config-leaf read). Plan-sync spawn stays UNCONDITIONAL — no gate branch, no probe call, no mode matrix, no per-task gate slot. The CROSS_SPEC line is the only 3e change.
- **Archive note (R5):** prepend to `optimization/plan-sync-gate/README.md` and `optimization/worker-anchor/README.md`: "ARCHIVED — the plan-sync skip-gate this harness validated was proven non-viable and removed from the shipped CLI (fn-83.4); see `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`. Kept as the evidence behind that decision." (worker-anchor stays live — its eval backs the shipped bundle; frame its note as "eval backs the shipped `flowctl anchor`.")
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
- [ ] `grep -rn 'plan.sync.probe\|planSync.gate\|plansync-gate' plugins/flow-next/{scripts,skills,agents}` clean (no shipped references)
- [ ] worker.md Phase 1 = single anchor call + floor prose; no PLAN_DEVIATION line; no evidence-schema change
- [ ] CROSS_SPEC passed to every plan-sync spawn; spawn otherwise unconditional + byte-unchanged
- [ ] archive/eval notes on both optimization READMEs
- [ ] mirror regenerated + committed, parity green; smoke + full unittest green; no version bump

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
