---
satisfies: [R5, R6, R10]
---

## Description

> **fn-83.6 SHIP-GATE VERDICT (2026-07-03): FAIL — ship WITHOUT gate wiring.**
> Both R14 clauses failed on the cross-repo proof (1 false skip, production-history-confirmed:
> transcribe fn-25.3/commit 8f3565b2; aggregate true-negative skip-rate 1/15 = 6.7% vs ≥50%
> required). This task body is the FAIL branch: unconditional plan-sync spawn retained — no
> gate branch, no mode matrix, no audit sampling, no probe invocation from phases.md. The
> probe + ledger stay in flowctl as UNWIRED dev assets. R7 (audit sampling) lapses with the
> gate. Evidence: `optimization/plan-sync-gate/cross-repo/README.md`.

Wire the SURVIVING fn-83 pieces into the skills/agents: worker evidence completeness (`base_commit` + full commit list), the PLAN_DEVIATION rubric + terminal line, the single anchor call, the CROSS_SPEC latent-bug fix, prefix-anchored terminal-line parsing prose, and the R6 config removal (`planSync.gate` enum + its tests deleted — no user config either way, per the user decision 2026-07-03). Depends on fn-83.1 (probe) + fn-83.2 (safety proof) + fn-83.6 (cross-repo ship gate — FAILED, so gate wiring is OUT of scope) + fn-83.3 (anchor).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/agents/worker.md`, `plugins/flow-next/agents/plan-sync.md` (caller-contract note only, if needed), `plugins/flow-next/scripts/flowctl.py` (R6 config-enum removal), regenerated mirror (validate locally; commit with this task)

## Approach

- **phases.md 3e — spawn semantics UNCHANGED:** plan-sync is spawned unconditionally whenever `planSync.enabled` is true (today's behavior). Do NOT invoke `plan-sync-probe` from phases.md; no gate branch, no mode matrix, no audit counter, no per-task gate summary slot, no `--record` calls. The only 3e edit is the CROSS_SPEC fix below.
- **CROSS_SPEC fix:** spawn prompt (currently :379-388) gains `CROSS_SPEC: <planSync.crossSpec value>` — the documented plan-sync.md:19 input the caller never passed (latent bug).
- **worker.md evidence completeness (R5 — still ships; feeds provenance + any future gate attempt):** capture `BASE_COMMIT=$(git rev-parse HEAD)` at Phase-1 end (before any edit); at done-time include additive `base_commit` + the full `git rev-list --reverse $BASE_COMMIT..HEAD` list in the `flowctl done` evidence JSON (multi-commit fix-loop tasks fully covered; evidence schema additive — no migration).
- **worker.md:** Phase 1 replaces the discrete anchor reads with one `flowctl anchor <TASK_ID> --md` call + explicit floor-not-ceiling prose (memory keyword-search + read-more freedom retained; Investigation targets/Design context reads unchanged in Phase 1.5). Phase 6: mandatory `PLAN_DEVIATION: yes|no` line with the explicit yes-trigger RUBRIC — API/function/name change beyond spec; contract/schema change; file set differs from Files list; scope grew/shrank; AC satisfied differently; dependency assumptions changed; glossary/strategy-relevant wording introduced; test plan diverged; ANY uncertainty ⇒ yes (placed immediately before the DELEGATION lines) — plus a prose regression test asserting rubric + grammar survive in canonical AND mirror, and the host-side parsing prose (phases.md 3d area) states all three terminal lines are parsed by anchored prefix regex over the whole return, last match wins, missing/malformed PLAN_DEVIATION ⇒ yes. (The flag is recorded for observability and any future gate attempt — nothing consumes it as a gate input.)
- **R6 config removal:** remove the `planSync.gate` enum from get_default_config + delete test_plansync_gate_config.py. The probe's `_psp_gate_mode` default already resolves `"off"` when the key is absent — no probe code change needed; the probe/ledger stay as unwired dev assets validated by the fn-83.2 corpus CI.
- **Mirror: regenerate AND COMMIT here with this task's canonical edits** (single sync-codex run; parity guards green; PLAN_DEVIATION + anchor call intact in mirror) — avoids dirty-generated-files/stash awkwardness under the work protocol's `git add -A`. fn-83.5 re-runs sync-codex as an idempotency verification (expected no-op diff).

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-work/phases.md:315-395` — 3d terminal parsing + 3e block (post-fn-82 state)
- `plugins/flow-next/agents/worker.md:21-111,425-480` — Phase 1 reads + Phase 6 return grammar + DELEGATION lines
- `plugins/flow-next/agents/plan-sync.md:13-24` — input contract (CROSS_SPEC)
- `optimization/plan-sync-gate/cross-repo/README.md` — the FAIL verdict this task's scope is bound by

## Key context

Ralph/autonomous: unchanged — plan-sync spawn stays unconditional; no new receipts, no prompts. The gate ledger is never written by the skill layer (nothing calls `--record`). If a future spec re-attempts the gate, it starts from the cross-repo corpus + the transcribe-02 false-skip exhibit — not from re-wiring this task.

## Acceptance

- [ ] phases.md 3e: unconditional plan-sync spawn retained — zero references to plan-sync-probe/gate/ledger/audit in the skill layer; CROSS_SPEC passed to every plan-sync spawn (single config-leaf read)
- [ ] worker.md: single anchor call + floor prose; PLAN_DEVIATION emitted per rubric; prefix-anchored parsing prose for all three terminal lines; prose regression test green (canonical + mirror)
- [ ] base_commit + full commit list recorded in done evidence (fixture-verified)
- [ ] `planSync.gate` config enum removed + test_plansync_gate_config.py deleted; fn-83.2 corpus CI still green (probe behavior unchanged)
- [ ] mirror regenerated + committed with this task, parity green; smoke + pytest green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
