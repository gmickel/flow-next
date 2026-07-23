---
satisfies: [R13, R14, R15, R16]
---
# fn-118-work-skill-sanctioned-parallel-worker.1 Expose prompt-guided parallel waves in plan and work

## Description
Update the canonical plan, work, and worker skills so the planner exposes dependency-ordered execution waves and the work conductor prefers safe parallel dispatch from the ready frontier. Keep concurrency, isolation, and integration as host-agent judgments. Parallel workers reuse the existing host-deferred shape: implement/test/commit, write task-unique handover evidence, and return without `flowctl done`; the conductor integrates and applies existing shared lifecycle steps.

**Size:** M

**Files:** `plugins/flow-next/skills/flow-next-plan/steps.md`, `plugins/flow-next/skills/flow-next-work/SKILL.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/agents/worker.md`, `plugins/flow-next/tests/test_parallel_work_prose.py`, generated `plugins/flow-next/codex/skills/flow-next-plan/**`, generated `plugins/flow-next/codex/skills/flow-next-work/**`, generated `plugins/flow-next/codex/agents/worker.md`

### Approach

- Strengthen the existing disjoint-file planning guidance; do not add another planning subsystem.
- After task creation/validation, require a compact execution-wave summary derived from the dependency DAG the planner authored.
- Replace the strictly sequential Phase 3 wording with ready-frontier/wave guidance: claim selected tasks, choose safe isolation using host capabilities, dispatch concurrently, join, integrate, then run existing verification/review/completion/tracker behavior.
- Add a parallel-wave worker mode by reusing the host-deferred contract: task-unique summary/evidence paths, commit and return before `done`, no tracker/plan-sync/integration ownership.
- Treat file ownership as agent evidence, not a deterministic parser contract; shared resources or uncertainty serialize.
- Require compact progress/fallback reporting.
- Add focused prose tests for the canonical and generated Codex surfaces.
- Run `scripts/sync-codex.sh` twice and compare the generated tree after the first and second run.

### Investigation targets

**Required** (read before coding):

- `plugins/flow-next/skills/flow-next-plan/steps.md:57-64` — current parallel-friendly decomposition guidance.
- `plugins/flow-next/skills/flow-next-plan/steps.md:412-426` — task creation/dependency contract.
- `plugins/flow-next/skills/flow-next-work/SKILL.md:203-207` — conductor/worker boundary.
- `plugins/flow-next/skills/flow-next-work/phases.md:181-210` — sequential loop to generalize.
- `plugins/flow-next/skills/flow-next-work/phases.md:381-437` — plan-sync and loop semantics.
- `plugins/flow-next/agents/worker.md:399-481` — host-deferred handover and generic evidence paths.

**Optional** (reference as needed):

- `plugins/flow-next/skills/flow-next-worktree-kit/SKILL.md` — existing isolation option.
- `plugins/flow-next/tests/test_worker_anchor_prose.py` — canonical/mirror prose-test pattern.
- `scripts/sync-codex.sh` — mirror generation and guards.

### Key context

`flowctl ready --spec` already returns the whole ready frontier. Atomic claims prevent duplicate ownership but do not make concurrent Git/index/file mutations in one checkout safe. No new CLI, scheduler, manifest, fixed worker limit, deterministic integration algorithm, or path-overlap parser belongs in this task.
## Acceptance
- [ ] Planning guidance preserves cohesive M-sized tasks while preferring disjoint ownership and avoiding unnecessary dependency edges.
- [ ] The plan result prints dependency-ordered execution waves and clearly identifies same-wave parallel candidates.
- [ ] Work inspects the full ready frontier, claims the selected wave, and prefers concurrent dispatch when the host can isolate and integrate it safely.
- [ ] The host retains judgment over eligibility, worker count, isolation mechanism, integration, and fallback; uncertainty produces sequential execution with a short explanation.
- [ ] Parallel workers use isolated mutable workspaces and task-unique handover paths, commit and return before `flowctl done`, and never own tracker projection, plan-sync, or integration.
- [ ] The conductor joins the wave, reports outcomes, integrates successful work, then applies existing per-task verification/review/completion/tracker behavior.
- [ ] Compact progress reports the selected tasks, isolation choice, dispatch count, worker outcomes, join completion, and fallback reason.
- [ ] Downstream plan-sync and the next frontier wait until the current wave is joined/resolved.
- [ ] Focused canonical/Codex prose regressions pass.
- [ ] A snapshot comparison proves `scripts/sync-codex.sh` makes no second-run mirror changes.
- [ ] `python3 scripts/run_tests_parallel.py` passes.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
