# Conduct checklist — flow-next-deps

A correct run reads the spec graph once and reports blocking chains, parallel execution phases, the critical path, and anything unresolvable.

- [ ] The per-spec gather loop runs once into a cached file at a literal composed path, and the later steps read that same literal path instead of re-running the loop.
- [ ] The run stays read-only inspection — no `flowctl spec add-dep` / `rm-dep` and no edits to spec files; edge changes are reported as commands for the operator to run.
- [ ] Every open (non-`done`) spec appears in the report as either READY or BLOCKED with the specific deps that are blocking it.
- [ ] The Deadlocked / Unresolvable section is rendered whenever the jq result's `.deadlocked` is non-empty, with each spec's unresolved deps and a stated likely cause (cycle vs missing/closed dependency). A report that lists phases while silently dropping an open spec has broken this.
- [ ] Execution phases and the critical path are rendered from the computed `.phases`, not narrated from a reading of the spec titles.
