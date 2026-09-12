# Conduct checklist - /flow-next:flow

A correct run reads whatever it was given, routes from the shared routing reference, runs the routed stage skill, re-evaluates after each hop, and stops at the next human decision with a self-contained report.

- [ ] Under any autonomy marker the run stops with the `NEEDS_HUMAN:` line before any read, route, or dispatch. A transcript that routed or dispatched under a marker has broken this.
- [ ] Every hop names the matrix row it matched, and each row it names exists in `references/route-matrix.md`; a stage skill the run invokes is one that ships. A hop that invented a route, or invoked a retired skill, has broken this.
- [ ] A ready spec with no tasks has its route recorded (`spec set-no-plan` or `spec clear-no-plan`) before any mint, and a plan route names one of the four positive signals from `references/plan-vs-no-plan.md`. A plan route justified by risk, size, or file count has broken this.
- [ ] A bare invocation resolves its item down the Step 1 ladder (last touched in this conversation, current branch, uncaptured intent, next open spec) and routes it as if the id had been given; the ask is reached only when no rung resolves. A run that asked while the conversation had just captured a spec, or that picked one of several plausible open specs without an inline pick, has broken this.
- [ ] At most one blocking question per hop, and only after the fork was classified as a product or preference call; an observable fork shows an experiment or prototype in the transcript instead of a question.
- [ ] Every stage reached carries exactly one `stage: <name> - ran | skipped(<kind>: <detail>) | failed(...)` line in the final report, including a QA skip under `pipeline.qa=auto`. A stage with no line has broken this.
- [ ] The run ends at the PR (run from intent) or when merge is the only step left (open-PR run); the transcript contains no merge, no spec close, and no `/flow-next:pilot` or `/flow-next:land` dispatch.
- [ ] An `--explain` run prints the route, signal, skip and skip kind, and the rejected alternatives, and the transcript shows no write under `.flow/` and no stage dispatch.
