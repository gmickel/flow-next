# Conduct checklist — /flow-next:spec-completion-review

A correct run resolves one review backend, has that backend verify the combined implementation of a spec's tasks against the spec's requirements, loops fixes until SHIP or the round cap, and records the terminal completion status exactly once.

- [ ] Backend detection runs once — a single `flowctl review-backend` call (or an explicit `--review=` override) resolves the backend, and only that backend's `workflow-<backend>.md` enters context.
- [ ] The verdict comes from the backend's response, not the coordinator. A SHIP declared without a backend verdict, or a review the coordinator performed itself, has broken this.
- [ ] Findings are spec-compliance gaps — requirements that never became tasks, requirements split incompletely across tasks, scope drift, missing doc updates — not code-quality notes, which belong to impl-review.
- [ ] Each backend review command runs as one blocking foreground call with a long timeout, never backgrounded and polled.
- [ ] A NEEDS_WORK verdict is followed by fixes, tests, a commit, and a re-review in the same session or receipt; a delivered verdict is never re-framed as a transport failure to reclaim a round, and the reviewer sandbox is never widened.
- [ ] The terminal status is written once through the shared checkpoint — SHIP → `ship` and exit 0, capped NEEDS_WORK → `needs_work` with `ESCALATE:` and exit 4, NEEDS_HUMAN → `needs_human` with `ESCALATE:` and no further reserve or dispatch.
