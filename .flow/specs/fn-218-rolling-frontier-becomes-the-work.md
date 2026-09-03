## Goal & Context

`/flow-next:work` schedules tasks on the rolling frontier by default. fn-203 measured a 52.1% work-phase wall saving for rolling admission with isolated worktrees at the decisive band (A1, study `rolling-frontier-2026-08`), `/flow-next:work-rolling` has run end-to-end in the field on Claude Code, Cursor and Grok Build since #365, and graduation was decided on 2026-09-04 (fn-203 task 7). This spec executes that decision: the rolling scheduler becomes canonical Phase 3, the wave loop remains as the structural fallback for the shapes where rolling has nothing to schedule, and the beta skill is deleted in the same change (fn-203's recorded outcome: exactly one topology remains).

The route is decided from spec state alone, never from a config knob or a host table:

- **Wave (existing 3a-3g, unchanged) when any of these hold:** `planSync.enabled` is not `false` (plan-sync's per-wave barrier is the existing fail-closed rule); the spec has fewer than two open tasks (a no-plan implicit task, or a single remaining task); or no two open tasks are dependency-independent under the transitive `depends_on` closure (a fully sequential chain admits one lane at a time, and the canonical single-worker path is the cheaper way to run one lane).
- **Rolling (the moved scheduler) otherwise.** Everything the scheduler already handles at runtime stays where it is: the five-condition admission rule (Touches disjointness, dep closure, cap 3, always-serial set), the honest degradation to wave-shaped dispatch on a host measured to block, the notes surface, per-return integration, conductor-owned review, and the plan-sync stage lines.

The scheduler's own `planSync=true` serial mode and its no-plan refusal are deleted: both were beta-only workarounds for a route decision the work skill can now make itself.

## Acceptance Criteria

- **R1:** `/flow-next:work <spec-id>` takes the rolling route by default. It takes the wave route only when `planSync.enabled` is not `false`, the spec has fewer than two open tasks, or no two open tasks are dependency-independent (transitive). The route and its reason are echoed once, at Phase 3 entry, as `Scheduling: rolling` or `Scheduling: wave (<reason>)`; the rolling scheduler's existing `degraded to wave (host lacks non-blocking dispatch)` line stays the only other value.
- **R2:** The rolling scheduler lives at `skills/flow-next-work/references/rolling-scheduler.md` and is read only when the rolling route is taken. The always-loaded work surface (SKILL.md, phases.md) grows by the route decision, its report line, and one pointer, judged under G1. `$WORK_SKILL` indirection is gone: the reference addresses sibling files directly.
- **R3:** Every rolling behaviour is preserved in substance under the new location: admission at every worker-return event with the five-condition rule, isolated per-task workspaces, conductor-owned review and `done`, `PARALLEL_WAVE: true` on every rolling dispatch, the plan-sync stage lines, the outside-tree notes surface, cross-run claim contention failing closed, and measured blocking-host degradation. The wave loop's semantics are unchanged.
- **R4:** The beta is deleted in the same change: `skills/flow-next-work-rolling/`, `commands/work-rolling.md`, the guide's experimental-variant paragraph and its no-plan clause, the `sync-codex.sh` entries (mirror skill list, `generate_openai_yaml`, the rewrite rules and their guard rows), the `adding-skills.md` experimental-tier note, and every test enumeration that counts it (`test_command_shim_flatten`, `test_chart_docs_inventory`, `test_chart_skill_contract`). No alias, no deprecation window.
- **R5:** `agent_docs/conduct/work.md` absorbs the rolling-delta items from `conduct/work-rolling.md` (route echo, admission report block, conductor-owned lifecycle, notes surface, claim contention) and the beta checklist file is deleted. Repo docs (`docs/README.md`, `skills.md`, `orchestration.md`, `architecture.md`, `pipeline-variations.md`, `platforms.md`, `troubleshooting.md`) describe rolling as work's default scheduler and the wave route as its fallback; the platforms matrix row moves from the beta to `/flow-next:work`. The docs site follows in the same workstream: `skills/work.mdx` gains the scheduler section; `skills/work-rolling.mdx`, its nav entry, the skills-index row, and the guide and choosing-your-route mentions go.
- **R6:** Pilot, land and Ralph dispatch plain `/flow-next:work` and never name the route; they inherit rolling with no change to their own prose. `## Unreleased` CHANGELOG entry (repo + docs site) written user-outcome-first: work is faster by default on multi-task specs, and the experimental skill is gone.

## Boundaries

- No config knob for the route; no host table lookup. The three wave conditions are spec state plus the existing plan-sync setting.
- No Touches-based route selection at the route level: Touches overlap is judged per admission inside the scheduler, exactly as today.
- No change to the wave scheduler's 3a-3g semantics, the concurrency cap (3), the review surfaces, or the worker agent.
- No compatibility alias for `/flow-next:work-rolling`.
- Tests pin tokens and structure only (G2): the route line, the reference's existence and pointer, the beta's absence. No prose assertions, no size ceilings.

## Quick commands

- `cd plugins/flow-next/tests && python3 -m unittest test_parallel_work_prose test_work_reached_path_routes test_command_shim_flatten test_skill_prose_diet test_skill_prose_flowctl_surface test_chart_docs_inventory test_chart_skill_contract -q`
- `./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short plugins/flow-next/codex`

## Decision Context

Rolling is the default rather than an opt-in route because the evidence question is closed: the A1 eval draw measured the saving at the decisive band, the beta's field runs on three hosts produced the receipts fn-203 R10 asked for, and the scheduler already carries every runtime fallback a conditional route would have needed (per-admission Touches judgment, measured blocking-host degradation). Gating rolling on spec shape or a platforms-matrix row would have re-introduced the conditional machinery the wall-clock research record rules out, and a docs table is not something a skill can read at runtime.

The three wave conditions are structural, not preferences. Plan-sync on is the existing fail-closed rule the beta already honoured by degrading to serial; making it a route condition lets the scheduler drop its own serial mode. Fewer than two open tasks is the beta's existing no-plan refusal, generalised: one lane has nothing to admit. A fully sequential dependency chain also admits one lane at a time, and the canonical single-worker path (worker in the conductor's checkout, worker-owned review and `done`) runs one lane with less machinery than a worktree plus a conductor integration per task.

The beta is deleted in the same change, with no alias, because fn-203 recorded that exactly one topology survives graduation and because pilot and land never named the beta, so nothing autonomous depends on the name. Rejected: a one-release alias (a second entry point for the same skill, which is the dual-surface state fn-203 R10 bounded), and keeping the scheduler's `planSync=true` serial mode (a duplicate of the wave route it now defers to).
