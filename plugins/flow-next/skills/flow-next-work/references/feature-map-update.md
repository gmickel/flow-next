# Feature-map update (gated reference)

> **Loaded only when `.flow/features/` exists**, at phases.md Phase 4 (Quality),
> after all tasks complete. A repo without a map never reads this file and the
> existence check is the whole cost.

The feature map records how a user reaches each feature. When this spec's change
alters one of those routes, the map is updated in the same change, so the PR
shows the map diff beside the code diff. Shape of a feature file and the drift
note contract: [feature-entry-contract.md](../../flow-next-features/references/feature-entry-contract.md).

This step is the only map writer besides `/flow-next:features`. It edits only
the entries this change altered; the full maintain pass stays user-invoked and
this step never dispatches it. It asks nothing, so it follows work's own
autonomy rules unchanged (attended, `mode:autonomous`, and Ralph runs alike).

## 1. Find the altered routes

Compare the spec's diff (`$(cat .flow/tmp/spec_base)..HEAD`, plus the task
done summaries, which name routes a task changed) with the map's feature files.
A route is altered when a user now reaches or drives a mapped feature
differently: a renamed control or label, a moved page or URL, a new entry point,
a removed sub-feature, or a changed CLI invocation. Code changes that leave
every mapped route as a user sees it are not map changes.

- No altered route: the map is untouched. Note `Feature map: unchanged` for the
  Phase 5 final summary and stop here.
- A changed user-facing surface that you cannot tie to one feature file: do not
  guess an edit. File a drift note naming the changed surface (title
  `drift: <surface>/<changed-surface-slug> unmapped`, Expected: the old route
  if known, Observed: what the change did) and leave the map alone.
- A user-facing feature the map has never covered is not an altered route. The
  next maintain pass finds it; this step adds no new feature file.

## 2. Prove each new route once

Evidence goes under `.flow/tmp/work-features-<spec-id>/`, referenced by path.

1. Start the app as `.flow/features/README.md` states (baseline preconditions,
   an isolated port and profile this run owns). Read
   [doctor-and-proof.md](../../flow-next-features/references/doctor-and-proof.md)
   and run Doctor before the first drive.
2. Drive each altered route once: UI surfaces by the
   [drive skill](../../flow-next-drive/SKILL.md) universal flow, `cli` surfaces
   by running the command directly and capturing stdout, stderr and exit code.
   Capture the user action and the resulting state.
3. Tear down what this run started. Keep the evidence.

**The app cannot be started, or no driver is usable:** leave the map unchanged.
For each altered route, file a drift note (the contract's identity, Expected:
the mapped route, Observed: `not driven (<reason>); the change moved it to
<new route>`) so the next maintain pass picks it up. The work run is not
blocked by this.

A route that fails to prove is not written; file the drift note the same way.

## 3. Write the proven edits

For each proven route, edit only that feature file: the sections the change
altered (`Sub-features`, `How to get to it (user POV)`, `Driving it`,
`Gotchas`), keeping the four-H2 and `**Surface:**` contract, and refresh its
`**Last proven:** <UTC date> at <git rev-parse --short HEAD>` line. Update the
index row in `.flow/features/README.md` when sub-feature IDs changed. A feature
the change removed outright is a source-confirmed deletion: drop its file and
index row and record the removed surface in the summary.

Then retire every open drift note that names a route this step proved
(`$FLOWCTL features status --json` lists `open_drift` ids and titles):
`$FLOWCTL memory mark-stale <entry-id> --reason "route re-proven <date> at <short commit>" --json`.
Memory disabled: drift notes are neither filed nor retired; record the expected
changes in the run notes and the final summary instead.

The edits (and any memory files the drift steps touched) ride the Phase 5
commit with the rest of the change. Note one line for the Phase 5 final
summary: `Feature map: <n> file(s) updated, <m> drift note(s) filed, <k> retired`.

Done when: every altered route is either proven and written with a fresh
last-proven line, or recorded as a drift note with the map left unchanged; no
unaltered feature file was edited; nothing undriven entered the map.
