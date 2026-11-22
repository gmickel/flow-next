# Minted implicit task: dispatch shape and subagent license (gated reference)

> Read from [no-plan-route.md](no-plan-route.md) when the minted task goes to a worker, or
> before dispatching any subagent while implementing it.

## Dispatch shape for the minted task

The minted task is normally implemented inline (phases.md Phase 3). When it goes to a
worker instead, the standard multi-task.md 3c dispatch applies with these renderings. The 3a report still prints all
five report lines including `Selection rule:` — state: single minted implicit task;
the frontier is exactly one. The dispatch template's `FORBIDDEN:` field echoes declared
Touches and the minted task declares NONE, so the path ban is omitted — the field still
renders, carrying only the non-path clauses (no force-push; no rebase of the target);
the whole-spec surface is the point. `TIMEBOX:` applies unchanged. A run that printed a
path-ban `FORBIDDEN:` for this task has broken this.

## Judicious subagent use (minted-task dispatch prose)

Append the license below to the minted task's 3c dispatch prompt as extra prose.
worker.md itself gains no subagent prose, and plan-full workers get no such
license — judgment governs there (spec Decision Context). When the conductor implements the minted task inline
(phases.md Phase 3), the conductor is the owner and holds this license itself.

The worker prompt for the minted task carries a broad license: parallel implementation
of independent surfaces, background research, scouting — the SHAPE is chosen by the
harness at execution time, never prescribed here. The holder is the owner wherever the
owner runs: the in-host worker on the standard path, or the bridged child when
worker.md's Phase 1b hands the task over a CLI bridge — the long-task brief in
`flowctl usage --orchestration` carries the same license, and the worker passes this paragraph through
to the child verbatim. Wrappers, scouts, and conductors never fan out on the owner's
behalf (STRATEGY.md, "The owner holds the license"). A host without nested dispatch
degrades to serial, never errors; no capability probing. Commit ownership unchanged:
the owner is the only committer — hand subagents disjoint surfaces or serialize — and the
commit convention is the owner's path's (staging its changed files plus `.flow/`, and the single-commit convention
in-host; the long-task brief's checkpoint convention when the owner is a bridged child).
Join barrier: every dispatched subagent
is awaited and reconciled BEFORE staging, verification, and commit — no live writer
exists at staging time (same discipline as the wave-level workspace cleanup gate
in [wave-join.md](wave-join.md)).
