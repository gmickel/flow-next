# Conduct checklist — /flow-next:memory-migrate

A correct run lifts pre-fn-30 flat memory files into the categorized schema, one entry at a time, writing every result through `flowctl memory add` and printing a full migration report.

- [ ] Only `pitfalls.md`, `conventions.md`, and `decisions.md` at the `.flow/memory/` root are read. Any other memory-root markdown, and anything already under `.flow/memory/{bug,knowledge}/`, is left untouched.
- [ ] Classification happens one entry per tool call. A single call that classifies several entries together, or a run whose migrated count is short of the enumerated count, has broken this.
- [ ] Each entry starts from the mechanical `(track, category)` default derived from its source filename, and every override in the report carries a body-driven rationale.
- [ ] In `mode:autofix` the run asks nothing, takes the mechanical default on genuine ambiguity, and lists those entries as `needs-review` rather than guessing silently.
- [ ] Legacy originals are renamed into `.flow/memory/_migrated/<filename>.bak` only after consent, and never deleted; autofix leaves them in place and surfaces the rename as a recommendation.
- [ ] The full report is printed to stdout — files processed, entries migrated, overrides, needs-review, plus per-entry detail — and a re-run over already-migrated files logs "already migrated" and skips.
