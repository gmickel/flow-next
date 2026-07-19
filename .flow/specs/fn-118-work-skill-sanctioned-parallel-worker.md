# fn-118 work skill: sanctioned parallel worker dispatch for file-disjoint tasks

> STUB (2026-07-19, maintainer-requested during the fn-117 messaging research). Interview/plan before building.

## Goal & Context

The maintainer has long run multiple worker subagents in parallel on disjoint tasks of one spec by prompting into `/flow-next:work` ("run .2 and .3 in parallel - they touch disjoint files"). This works today because the host can batch multiple worker Task calls in one message and the state store makes claims atomic (flock in `flowctl start`, assignee collision checks) - but a full-history check (both plugin generations) confirms the skill prose NEVER sanctioned it: phases.md describes a strictly sequential per-task loop ("For each task, spawn a worker"). The capability is real, load-bearing in practice, and undocumented - which risks (a) a future prose tightening accidentally forbidding it, (b) agents refusing or serializing when prompted, (c) the fn-117 cookbook marketing a pattern the skill contract does not name.

Make it official: the work skill gains a sanctioned parallel branch.

## Sketch (design at plan time)

- Phase 3 gains an explicit parallel mode: when 2+ READY tasks have no dependency edges between them AND declare disjoint `**Files:**` lists (plan-time file-overlap minimization is the existing design guidance), the host MAY dispatch their workers in one parallel batch (multiple Task calls in one message). Triggered by user prompt ("in parallel") or an explicit flag (`--parallel[=N]`); default remains sequential (context-budget conservatism).
- Each worker keeps its full per-task contract unchanged (claim via `flowctl start`, implement, gates, review loop to SHIP, `flowctl done` with evidence, per-task commit). Verification (3d) runs per returned worker; plan-sync (3e) runs ONCE after the batch (downstream = remaining todo tasks).
- Overlap guard: tasks whose Files lists intersect (or that share a dep edge) are NEVER co-dispatched - fall back to sequential for those. Same-branch commits from parallel workers are serialized by git itself (workers commit at different times; a push race is not in scope - single-branch local commits only).
- Autonomous callers (pilot) stay sequential in v1 - this is an interactive/prompted capability first; pilot integration is a separate decision.
- Docs: work skill page + teams.md "Parallel work from one spec" gains the single-session variant; cookbook recipe in fn-117 updates from "prompted, works today" to "sanctioned contract" once this lands.

## Boundaries

- No flowctl changes expected (claims are already atomic; if a gap is found, it is a bug fix not a feature).
- Not Ralph-scoped (fresh-session-per-iteration model unchanged).
- Coordinate with fn-110 (skill fence consolidation touches the same phases.md).
