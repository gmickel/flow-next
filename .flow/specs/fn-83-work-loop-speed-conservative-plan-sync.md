# fn-83 Worker anchor bundle + cross-spec plan-sync fix (plan-sync skip-gate proven non-viable, shelved)

## Overview

fn-83 set out to speed the `/flow-next:work` loop two ways: (1) gate the after-every-task plan-sync agent behind a cheap deterministic probe, and (2) collapse the worker's ~8-read anchor into one call. Both were eval-gated on zero quality loss.

**The plan-sync skip-gate is proven non-viable and does NOT ship.** Cross-repo validation (fn-83.6: 27 real scenarios from DocIQ-Sphere/gno/transcribe against the real plan-sync agent) produced a genuine false skip (semantic drift no path/token can see) and a 6.7% skip-rate (needed ≥50%) — both fundamental, not tunable. Full analysis + "do not re-attempt" is captured in the decision record `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`. The gate machinery is removed from the shipped CLI; the experiment stays as archived evidence under `optimization/`.

**This spec now ships only the two independently-proven wins:** the `flowctl anchor` bundle (zero-loss, superset + comprehension proven) and the CROSS_SPEC latent-bug fix. Plan-sync continues to spawn unconditionally, exactly as before fn-83.

## Quick commands

```bash
(cd "$(mktemp -d)" && bash /Users/gordon/work/flow-next/plugins/flow-next/scripts/smoke_test.sh)
python3 -m unittest discover -s plugins/flow-next/tests            # incl. test_anchor_bundle.py
bash scripts/sync-codex.sh                                          # worker/phases edits mirror; flowctl shared
flowctl anchor <task-id> --md                                      # the shipped bundle
```

## What ships

**1. `flowctl anchor <task-id> [--json|--md]` — single-call worker anchor bundle (DONE, fn-83.3).** Assembles the worker's Phase-1 anchor from the verbatim output of the same production `cmd_*` functions the worker runs today (full task + spec bodies, deps with done-summaries, git state, memory/glossary indices) — byte-identical by construction, deterministic order, pure stdlib 3.8+. worker.md Phase 1 replaces its ~8 discrete reads with one call and keeps its read-more freedom (bundle is a floor). Proven zero-loss two ways: a byte-for-byte superset test and a comprehension-equivalence eval (bundle 7/7 ≥ status-quo 7/7 on 3 frozen real tasks, incl. a non-satisfies-section question).

**2. CROSS_SPEC caller fix.** The plan-sync spawn prompt (phases.md ~3e) never passed the `CROSS_SPEC` flag its own contract documents (plan-sync.md:19) — a latent bug that silently disabled cross-spec drift checking. The spawn now passes `planSync.crossSpec`. Independent of the gate; makes the existing unconditional plan-sync correct.

## What does NOT ship (removed from the shipped plugin)

- `flowctl plan-sync-probe` command + probe-specific `_psp_*` helpers (KEEP the shared `_psp_run_git` — `flowctl anchor` reuses it; relocate/rename as needed).
- `planSync.gate` config enum + the `plansync-gate.jsonl` ledger writer.
- The probe/gate/config tests: `test_plan_sync_probe.py`, `test_plansync_gate_config.py`, `test_plan_sync_gate_corpus.py` (removed; `test_anchor_bundle.py` stays).
- REMOVE the `PLAN_DEVIATION` worker terminal line (worker.md ~:430) + its parser prose (phases.md ~:285) — a dead gate SIGNAL whose only consumer (the probe) is gone.
- KEEP `BASE_COMMIT` and its evidence recording. It is load-bearing INDEPENDENT of the gate: it scopes the impl-review diff (`BASE_COMMIT..HEAD`, worker.md Phase 4), anchors delegation git-ownership/rollback (Phase 2), and records commit-range provenance in done evidence (Phase 5) — all predate or outlive fn-83. Only the removed probe CONSUMED `evidence.base_commit`; the field stays as general provenance. A naive `base_commit` removal would break impl-review/delegation and is explicitly forbidden.
- NO gate branch / mode matrix / audit sampling / per-task `plan-sync:` gate slot in phases.md. Plan-sync stays unconditional.

## Kept as archived evidence (dev assets, repo-root, NOT shipped in the plugin)

- `optimization/plan-sync-gate/` (this-repo corpus + frozen real-agent answer key + `cross-repo/` verdict) and `optimization/worker-anchor/` (the passing comprehension eval). Add a top-of-README "ARCHIVED — probe removed from flowctl in fn-83.4; kept as the evidence behind the decision record" note.

## Boundaries / non-goals

- NO plan-sync skip-gate in any form (see decision record — do not re-attempt).
- NO parallel task execution, NO review pipelining, NO review-backend changes.
- NO change to plan-sync's own prompt/judgment; the CROSS_SPEC fix is caller-side only.
- No user config added; no version bump (batched).
- flowctl stays pure-stdlib Python 3.8+.

## Strategy Alignment

Active tracks served:
- **Ralph autonomous mode** — worker anchors via one call instead of ~8 (faster per-task start, proven zero information loss); the CROSS_SPEC fix hardens autonomous plan-sync correctness.
- **Self-improving through normal work** — the gate experiment + cross-repo corpus are archived as a permanent "don't re-attempt" exhibit + decision record; memory-scout surfaces it to future plan-sync work.

## Decision context

- The skip-gate was killed by its own eval, which is the eval discipline working: a plausible optimization (deterministic drift prediction) was proven to cost quality (a real false skip) AND deliver no speedup (6.7% skip-rate), so it does not ship. Root cause: drift is semantic; a deterministic path/symbol probe cannot see it, and a semantic proxy is just a second LLM. Captured durably so it is not re-attempted.
- The anchor bundle survives because it is a pure round-trip reduction with a byte-level superset guarantee — no judgment, no prediction, provably no information loss.
- The CROSS_SPEC fix ships regardless — it is an existing-behavior bug fix surfaced during the work, not gate-dependent.
- The probe is REMOVED from the shipped CLI (not left as an "unwired dev asset") so it neither ships dead weight to users nor invites a re-attempt; the archived corpus under `optimization/` preserves the evidence.

## Acceptance Criteria

- **R1:** `flowctl anchor <task-id> [--json|--md]` ships (delivered in fn-83.3): verbatim single-call bundle, deterministic order, pure stdlib; superset test + comprehension-equivalence eval green and committed.
- **R2:** worker.md Phase 1 uses the single `flowctl anchor <TASK_ID> --md` call with explicit floor-not-ceiling prose (memory keyword-search + read-more freedom retained; Investigation-targets/Design-context reads unchanged).
- **R3:** CROSS_SPEC caller fix: every plan-sync spawn passes `planSync.crossSpec` (single config-leaf read); plan-sync spawn otherwise byte-unchanged (unconditional).
- **R4:** Gate machinery removed from the shipped plugin: `plan-sync-probe` + probe-specific `_psp_*` (EXCEPT the retained `_psp_run_git`, reused by `flowctl anchor`), `planSync.gate` config, the ledger writer, and the three probe/gate/config tests — all gone (two grep guards clean: user-surface `plan.sync.probe|planSync.gate|plansync-gate` AND symbol-level `cmd_plan_sync_probe|PLANSYNC_GATE_LEDGER|_psp_` with an explicit `_psp_run_git`-only whitelist); `flowctl anchor` + `test_anchor_bundle.py` intact. The `PLAN_DEVIATION` line + parser prose are DELETED (dead gate signal). `BASE_COMMIT` + its evidence recording are RETAINED unchanged (load-bearing for impl-review diff-scoping + delegation + provenance; only the probe's consumption is gone).
- **R5:** Decision record `plan-sync-skip-gate-not-viable-2026-07-03.md` committed; `optimization/plan-sync-gate/` + `optimization/worker-anchor/` carry the ARCHIVED-evidence note.
- **R6:** Docs (streamlined): flowctl.md `anchor` command section (house style); GLOSSARY `Re-anchoring`/`Worker subagent` light refresh (single-call bundle); optimizing-skills.md pointer to `optimization/worker-anchor/`; optimization-log.md rows (anchor eval PASS, gate FAIL/shelved); NO `planSync.gate` doc surface anywhere (repo or docs-site). CHANGELOG `## Unreleased` entry (anchor bundle + CROSS_SPEC fix; gate recorded as shelved with the decision-record pointer).
- **R7:** Docs-site (same workstream, ~/work/flow-next.dev): plan-sync stays documented as unconditional (no gate config, no mermaid gating, no footnotes); the anchor round-trip win is the only documentable change; `pnpm build` green; no FLOW_NEXT_VERSION bump.
- **R8:** Mirror regenerated + committed (parity green); PR body carries the anchor round-trip before/after table + a one-paragraph honest note that the skip-gate was proven non-viable (pointer to the decision record) — not sold as a shipped feature.
- **R9:** smoke (non-repo cwd) + full unittest suite green; no version bump (batched).

## Early proof point

The shipping wins are already proven — `flowctl anchor` passed both its superset test and comprehension eval in fn-83.3. The remaining risk is purely surgical: removing the probe without breaking the anchor's shared `_psp_run_git` dependency (fn-83.4's first check).

## Requirement coverage

| Req | Description | Task(s) | Notes |
|-----|-------------|---------|-------|
| R1  | flowctl anchor + proofs | fn-83.3 (done) | shipped |
| R2  | worker.md single anchor call | fn-83.4 | — |
| R3  | CROSS_SPEC caller fix | fn-83.4 | — |
| R4  | remove gate machinery from shipped CLI | fn-83.4 | keep `_psp_run_git` |
| R5  | decision record + archive note | fn-83.4 | record written during streamline |
| R6  | repo docs + CHANGELOG | fn-83.5 | — |
| R7  | docs-site | fn-83.5 | — |
| R8  | mirror + PR evidence | fn-83.4 (mirror), fn-83.5 (PR) | — |
| R9  | gates, no bump | fn-83.4, fn-83.5 | — |

*Historical: fn-83.1 (probe), fn-83.2 (this-repo corpus + proof), fn-83.6 (cross-repo verdict) are DONE — they produced the evidence that shelved the gate. Their shipped-CLI code is removed by R4; their optimization/ evidence is kept by R5.*
