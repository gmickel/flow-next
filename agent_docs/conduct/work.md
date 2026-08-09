# Conduct checklist — /flow-next:work

A correct run executes a spec or task end to end — branch setup, fresh-context workers per task, review, quality gates, and a final summary — with all task state read and written through `flowctl`.

- [ ] Task state moves only through `flowctl start` and `flowctl done`, and each completion is confirmed by `flowctl show <task-id> --json` reporting `done` before completion is claimed. A session that tracks tasks with TodoWrite or a markdown plan file outside `.flow/` has broken this.
- [ ] The branch question is answered before any file is read or code written; under autonomy the run defaults to a new branch named exactly the spec's `branch_name` field rather than an ad-hoc name.
- [ ] Each task is implemented by a fresh-context worker subagent, and the frontier decision is reported before claiming (`Ready frontier`, `Selected wave`, `Isolation`, `Dispatch count`, and a sequential-fallback reason when one applies). A wave dispatched with a missing or overlapping `**Touches:**` declaration has broken this.
- [ ] When the resolved review mode is `host-deferred`, the conductor runs `/flow-next:impl-review` itself against the task's re-read base and only calls `flowctl done` after a SHIP verdict, with review-fix commits and the receipt appended to that task's evidence.
- [ ] Every stage the run reached records one stage-outcome line in the receipt surface it already writes — plan-sync included, whether it ran, skipped with a reason, or failed. A stage with no line reads as failed.
- [ ] The run closes with the mandatory final summary block, including a `Tracker sync:` slot in one of its four states (`n/a (bridge inactive)` when no tracker is configured) and one `Gates:` line per accumulated Phase 4 outcome.
- [ ] When the Phase 4 quality audit fires, both axes are dispatched in a single message — one `AXIS: correctness` and one `AXIS: standards` call to the same auditor agent. A transcript that sent one axis, read its report, and only then sent the other has broken this.
- [ ] Both axis reports are surfaced verbatim under `### Correctness axis` and `### Standards axis`, followed by one count-plus-worst-tier line per axis. A merged, reranked, or interleaved findings list, or an axis dropped because the other looked worse, has broken this.
- [ ] No Critical finding is attributed to the standards axis — its charter ceiling is Should Fix, so a standards-axis Critical is reported as a charter break rather than actioned as a blocker.
