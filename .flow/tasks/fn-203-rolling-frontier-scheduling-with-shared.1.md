---
satisfies: [R1]
---
# fn-203-rolling-frontier-scheduling-with-shared.1 Pre-register the three-arm eval: fixture, endpoints, harness design

## Description
Produce the frozen pre-registration for the R1 eval before any prototype draw runs. This is study design only - no product files change.

**Size:** M
**Files:** pre-registration + fixture live in the maintainer's eval workspace (outside this repo); no repo files modified
**Touches:** []

### Approach
- Select or author the fixture spec: >=5 tasks, >=4 admissible task boundaries (dep-independent, disjoint Touches). Minimum valid size - 5 tasks, not more; the fixture exists to fix the prior measurement's minimum-surface confound, not to maximize runtime. If authored, freeze its plan and task files at a pinned SHA so all arms draw from identical input.
- Freeze endpoints and decision rules per R1: primary quality parity (blind checklist + full deterministic suites), secondary work-phase wall-clock and the five incident classes, the >=15% ship gate, zero-uncontained-incidents clause, tiebreaker, INCONCLUSIVE as first-class.
- Freeze the model configuration: conductor and workers on the production default (opus-5 at medium effort), identical across all arms and draws - never the planning session's escalation-tier model. Record the exact model ids and effort in the registration so draws are reproducible.
- Freeze the supervision budget and abort rules, wall-clock-first (tokens are the backstop, not the constraint), with EXACT numbers - no discretionary terms survive into the registration. Per-draw: kill any treatment draw exceeding 1.5x its batch's baseline draw duration (baseline runs first, so W0 is known live; a rolling arm slower than the barrier has already failed); kill a draw whose current task exceeds 3x the baseline draw's median task time beyond the existing review-cap/stall-guard bounds (provisional per-task ceiling 100 min until the baseline draw completes); absolute wall ceiling 8h per draw; token backstop 20M per draw, runaway detection only. Per-arm aggregates across the whole study: 24h wall and 60M tokens; exhausting an arm's aggregate records that arm INCONCLUSIVE (baseline exhaustion terminates the study INCONCLUSIVE). Killed draws are invalidated, not scored; an invalidated draw voids its batch, and each batch gets at most 2 attempts (one re-run) - a second invalidation records the affected arm(s) INCONCLUSIVE.
- Freeze the batch and futility plan with exact cardinality and bands: one batch = 3 arms x 1 draw each, run SEQUENTIALLY on one otherwise-idle machine (paired same-machine draws per R1; sequential execution removes cross-arm interference from every gating draw): baseline first (enables the live 1.5x kill rule), then the two rolling arms in randomized order; host load recorded per draw; residual time-of-day/order drift is a declared limitation. Decisive pass per rolling arm: saving >= 20% with quality parity and zero uncontained incidents. Decisive fail: saving < 10%, or any uncontained incident, or quality regression. Borderline (saving in [10%, 20%) with parity and zero uncontained): exactly ONE replication batch, same sequential shape with re-randomized treatment order, verdict = pooled mean saving across both batches vs the 15% gate with incidents pooled. INCONCLUSIVE (first-class): after replication, |pooled saving - 15%| <= between-batch spread of that arm's saving. No other outcome-based early stopping exists.
- Freeze the blind-scoring redaction contract: scorer sees only the final integrated diff + suite results; commit history and notes artifacts stripped (arm-2 output is structurally distinctive - the redaction is what keeps scoring blind).
- Freeze harness isolation: each draw in its own isolated checkout with its own runtime state dir (set the state-dir env per draw); paired same-machine sequential draws per the batch plan above.
- Freeze all three arm-2 disciplines (staging-by-declaration, branch-local lock, edit-state ledger) as part of the registration.

### Key context
- Draws must not share claim/receipt state: the runtime state store resolves through the git common dir and is shared across sibling worktrees unless the state-dir env is set per draw.
## Acceptance
- [ ] Fixture spec exists, satisfies the >=5-task / >=4-boundary shape at minimum valid size, and is pinned
- [ ] Pre-registration frozen before any draw: endpoints, decision rule, model config (opus-5 at medium), wall-first budgets + kill rules, batch/futility plan, redaction contract, isolation design, arm-2 disciplines
- [ ] No files in this repo modified
## Done summary
Pre-registered the fn-203 three-arm rolling-frontier eval before any draw: study frozen at agent-evals/studies/rolling-frontier-2026-08 (PREREGISTER.md + README + changelog + fixtures registry; commits fddf70c/790d6e3/e6f... see repo log), fixture authored and pinned at flow-swarm branch eval/fixture-rolling-frontier @ 01b89740 (fn-174, 5 dep-independent tasks, Touches pairwise disjoint across all 10 pairs, 4 admissible boundaries at cap 3, leak-checked pre-impl at parent 80f668c6, flowctl-readable). Registration freezes endpoints (blind sealed checklist + full suites; wall-clock; 5 incident classes), exact decision bands (>=15% gate, decisive 20%/10%, INCONCLUSIVE first-class), model config (claude-opus-5 @ medium, all arms/draws), wall-first budgets with per-arm aggregates and bounded reruns, sequential baseline-first gating draws, redaction contract, per-draw isolation (own checkout + FLOW_STATE_DIR), and all three arm-2 disciplines. No product files modified in this repo; flow-next commits are the fn-203 plan artifacts + review-driven plan fixes (task ordering .4->.5 dep, manifest regen wording, field-window authority in spec, lifecycle Touches).

stage: impl-review - ran [r1 NEEDS_WORK (6 findings), r2 NEEDS_WORK (2 survivors), r3 SHIP] via codex/gpt-5.6-sol
## Evidence
- Commits: 8bb40cd3051c3b18bf1ac0c33fd43aa39e308b5a, 61fa639e1ee963af69f97fd93608b2ff31b91117, 72e035e65fdb792c8a84ccf747e4b32aec10458b
- Tests: baseline: green (cd plugins/flow-next/tests && python3 -m unittest test_parallel_work_prose test_worker_anchor_prose test_cp1252_robustness -q), cd plugins/flow-next/tests && python3 -m unittest test_parallel_work_prose test_worker_anchor_prose test_cp1252_robustness -q (re-run green after review fixes), uvx ruff@0.16.0 check ., GATE_SKIPPED:unittest:docs-only - cumulative diff classified tier-B (no executable paths touched)
- PRs:
stage: plan-sync - ran (no drift; no downstream edits)
