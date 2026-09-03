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
Pre-registered as agent-evals studies/rolling-frontier-2026-08 (PREREGISTER.md frozen before any draw; fixture flow-swarm fn-174 pinned 01b89740; ship gate 15% work-phase wall at quality parity, decisive band 20%). Closed retroactively on 2026-09-04: the work happened on 2026-08-21/22 and the task state was never updated when #365 squash-merged.
## Evidence
- Commits: c821b999, afdf5e57
- Tests: agent-evals studies/rolling-frontier-2026-08 (PREREGISTER.md frozen pre-draw; A0 129.1 min, A1 61.9 min, 52.1% saving, decisive band)
- PRs: https://github.com/gmickel/flow-next/pull/365, https://github.com/gmickel/flow-next/pull/376