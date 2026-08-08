# Conduct checklist — flow-next task management

A correct run answers quick `.flow/` questions and performs small task and spec operations — listing, showing, creating, starting, completing — entirely through the bundled `flowctl`.

- [ ] `$FLOWCTL` is resolved from the bundled preamble path before first use, and a failing `which flowctl` is treated as expected rather than as a missing install.
- [ ] Reads use `flowctl` with `--json` (`detect`, `list`, `specs`, `tasks`, `show`, `ready`) or `cat` for markdown, so the answer comes from `.flow/` state rather than from files skimmed by hand.
- [ ] Every write goes through a `flowctl` subcommand. A session that edits `.flow/` JSON or task markdown directly instead of going through flowctl has broken this.
- [ ] "Add a task for X" locates the owning spec first, then creates the task and sets its description and acceptance via `task set-spec` (or the stdin form), leaving the new task with both fields populated.
- [ ] A task marked complete is closed with `flowctl done` carrying both a summary file and an evidence JSON, not a bare status flip.
- [ ] Requests that need real planning or execution are handed to `/flow-next:plan` and `/flow-next:work` rather than improvised here.
