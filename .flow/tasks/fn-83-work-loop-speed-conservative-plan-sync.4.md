---
satisfies: [R5, R7, R10]
---

## Description

Wire it all into the skills/agents: phases.md 3e gate branch (mode matrix + audit sampling + summary slot), worker.md (PLAN_DEVIATION line + single anchor call), CROSS_SPEC latent-bug fix, prefix-anchored terminal-line parsing prose, mirror validation. Depends on fn-83.1 (probe) + fn-83.2 (the PROOF — wiring/default-on never lands before the corpus check passes) + fn-83.3 (anchor).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/agents/worker.md`, `plugins/flow-next/agents/plan-sync.md` (caller-contract note only, if needed), regenerated mirror (validate locally; commit per repo convention for this spec's tasks — single regen at fn-83.5)

## Approach

- **phases.md 3e (current anchor :347-390 — relocate by content):** keep the `planSync.enabled` outer check (matrix: enabled=false ⇒ 3e skipped entirely, gate irrelevant). Inside: read `planSync.gate` once (LEAF pattern); `off` ⇒ today's spawn path, probe not invoked; `shadow` ⇒ run probe with `--record shadow` + worker's deviation value, ALWAYS spawn, record actual verdict via record-actual after plan-sync returns; `on` ⇒ probe decides; skip ⇒ deterministic RAMPED audit counter from the ledger's skip_index (1-in-2 for the repo's first 20 skips, 1-in-5 thereafter; spawns anyway with `--record audit`; pairing recorded; a `Drift detected: yes` on an audit spawn = **AUDIT MISS** — surface loudly in the summary + ledger + instruct flipping to shadow; NEVER auto-mutate config). Per-task `plan-sync:` slot in the final summary in ALL modes: `spawned (<reason>) | skipped (<proof>) | shadow: would-<decision> | audit: <outcome>`. Follow the fn-82 gate-skeleton rules (no pipelines, rc-checked, fail-open ⇒ spawn).
- **CROSS_SPEC fix:** spawn prompt (currently :379-388) gains `CROSS_SPEC: <planSync.crossSpec value>` — the documented plan-sync.md:19 input the caller never passed. Probe and spawn read the same config leaf once.
- **worker.md evidence completeness (load-bearing for the probe):** capture `BASE_COMMIT=$(git rev-parse HEAD)` at Phase-1 end (before any edit); at done-time include additive `base_commit` + the full `git rev-list --reverse $BASE_COMMIT..HEAD` list in the `flowctl done` evidence JSON (multi-commit fix-loop tasks fully covered; evidence schema additive — no migration).
- **worker.md:** Phase 1 replaces the discrete anchor reads with one `flowctl anchor <TASK_ID> --md` call + explicit floor-not-ceiling prose (memory keyword-search + read-more freedom retained; Investigation targets/Design context reads unchanged in Phase 1.5). Phase 6: mandatory `PLAN_DEVIATION: yes|no` line with the explicit yes-trigger RUBRIC — API/function/name change beyond spec; contract/schema change; file set differs from Files list; scope grew/shrank; AC satisfied differently; dependency assumptions changed; glossary/strategy-relevant wording introduced; test plan diverged; ANY uncertainty ⇒ yes (placed immediately before the DELEGATION lines) — plus a prose regression test asserting rubric + grammar survive in canonical AND mirror, and the host-side parsing prose (phases.md 3d area) states all three terminal lines are parsed by anchored prefix regex over the whole return, last match wins, missing/malformed PLAN_DEVIATION ⇒ yes.
- **Mirror: regenerate AND COMMIT here with this task's canonical edits** (single sync-codex run; parity guards green; PLAN_DEVIATION + anchor call intact in mirror) — avoids dirty-generated-files/stash awkwardness under the work protocol's `git add -A`. fn-83.5 re-runs sync-codex as an idempotency verification (expected no-op diff).

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-work/phases.md:315-395` — 3d terminal parsing + 3e block (post-fn-82 state)
- `plugins/flow-next/agents/worker.md:21-111,425-480` — Phase 1 reads + Phase 6 return grammar + DELEGATION lines
- `plugins/flow-next/agents/plan-sync.md:13-24` — input contract (CROSS_SPEC)
- fn-82 gate-skeleton precedent: `plugins/flow-next/skills/flow-next-work/SKILL.md` bridge gate + `references/tracker-touchpoints.md` gate prose

## Key context

Ralph/autonomous: gate rides receipts + summary slots, never prompts; audit miss surfaces identically. The deterministic audit counter state lives in the gate ledger (count skips per spec from the jsonl — no new state file).

## Acceptance

- [ ] 3e mode matrix implemented per Approach; summary slot present in all modes; audit counter deterministic; AUDIT MISS loud; config never auto-mutated
- [ ] CROSS_SPEC passed to every plan-sync spawn; single config-leaf read
- [ ] worker.md: single anchor call + floor prose; PLAN_DEVIATION emitted; prefix-anchored parsing prose for all three terminal lines
- [ ] base_commit + full commit list recorded in done evidence (fixture-verified); mirror regenerated + committed with this task, parity green; smoke + pytest green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
