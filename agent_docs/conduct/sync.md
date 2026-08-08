# Conduct checklist — /flow-next:sync

A correct run manually triggers plan-sync so downstream task specs are updated after implementation drift, from a resolved source task to the spec's remaining `todo` and `blocked` tasks.

- [ ] The supplied id is routed through `flowctl show <id> --json` rather than a hard `fn-` prefix check, so a tracker handle such as `wor-17` resolves to its linked spec or task. A session that rejects a resolvable handle as an unknown id has broken this.
- [ ] A source task is anchored before any downstream work: the input task in task mode, or the most recently updated `done` (else `in_progress`) task in spec mode, with the documented refusal when neither exists.
- [ ] The downstream set is the spec's `todo` and `blocked` tasks with the source task excluded, and a run with an empty downstream set stops with the "No downstream tasks to sync" outcome instead of spawning an agent.
- [ ] Glossary, decisions, and strategy context are gathered best-effort with the empty defaults preserved on failure, and the husk short-circuit passes empty defaults through when all three carry no signal.
- [ ] `planSync.crossSpec` is read and passed to the agent as a literal `true` or `false`, so a repo opted into cross-spec propagation gets the same behavior here as from the work-loop auto-trigger.
- [ ] The task-spec edits are made by the spawned `flow-next:plan-sync` agent, and a `--dry-run` invocation reports drift and closes with "No files modified." A session that edits downstream task specs directly has broken this.
