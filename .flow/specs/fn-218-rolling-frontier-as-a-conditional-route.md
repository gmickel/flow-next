## Goal & Context

Teams get the rolling frontier by default inside `/flow-next:work`, without learning a second skill. fn-203 measured a 52% work-phase wall saving for rolling admission with isolated worktrees at the decisive band, and `/flow-next:work-rolling` has run in the field since #365 on Claude Code, Cursor and Grok Build. Graduation was decided on 2026-09-04 (fn-203 task 7). This spec folds the rolling scheduler into the official work skill as a conditional route: the skill's dispatch step decides wave vs rolling from the spec's shape and the host's measured dispatch behaviour, loads the rolling references only on that route (progressive discovery: the always-loaded surface does not grow by the rolling prose), and `work-rolling` becomes a thin alias for one release before retirement. The rolling references, notes surface, plan-sync barrier and conductor-owned review lifecycle move under the work skill's references directory unchanged in substance.

STUB: the route condition, the alias window, and the docs shape are the decisions to interview before planning.

## Acceptance Criteria

- **R1:** `/flow-next:work <spec-id>` selects the rolling route when the spec has two or more dep-independent tasks with pairwise-disjoint Touches and the host is a measured non-blocking dispatcher (per the platforms matrix); otherwise the wave route. The choice and its reason are echoed once in the run report.
- **R2:** The rolling references load only on the rolling route (progressive discovery); the always-loaded work surface (SKILL.md, workflow.md, phases.md) grows by the route decision and a pointer only, judged under G1.
- **R3:** Every rolling-only behaviour (per-task admission at worker return, isolated workspaces, conductor-owned review lifecycle, plan-sync barrier, notes surface outside the tree, blocking-host degradation to waves) is preserved byte-for-byte in substance under the new location; the fn-169-style no-embed test that drives the real dispatch path covers the rolling route.
- **R4:** `/flow-next:work-rolling` remains for one release as an alias that forwards to `work` with the rolling route forced and prints a one-line deprecation notice; the release after removes it. Docs, docs-site, platforms matrix and CHANGELOG say so.
- **R5:** `--no-plan` and single-task specs never take the rolling route (a single implicit task degenerates the frontier), matching the current refusal.

## Boundaries

- No new config knob for the route; the condition is spec shape plus measured host behaviour.
- Pilot and land dispatch plain `work`; they never name the route.
- No change to the wave scheduler's semantics.

## Quick commands

- `cd plugins/flow-next/tests && python3 -m unittest test_work_rolling test_work_dispatch test_skill_prose_flowctl_surface -q`
- `./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short plugins/flow-next/codex`

## Decision Context

Rolling graduates as a route inside work rather than a default replacement of the wave scheduler because a genuinely blocking host and a single-task spec still need waves; the route condition makes the fallback structural, never a knob. Progressive discovery keeps the always-loaded surface flat, which is the G1 discipline the repo already enforces.
