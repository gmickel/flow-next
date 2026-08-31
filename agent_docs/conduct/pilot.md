# Conduct checklist — /flow-next:pilot

A correct tick selects one ready spec, classifies one pipeline stage, dispatches exactly one stage skill, verifies state advanced, and ends with one terminal `PILOT_VERDICT` line.

- [ ] The response ends with exactly one `PILOT_VERDICT` line and nothing after it. A tick that advances two stages, or that prints prose below the verdict, has broken this.
- [ ] Exactly one stage skill is dispatched from `{plan, plan-review, work, make-pr}`, plus `qa` only when `pipeline.qa==on`. Merge, land, resolve-pr, capture, interview, and chart never appear as a pilot stage.
- [ ] The tick asks the user nothing; ambiguity, a sub-skill crash, or a failed gh probe resolves as `NEEDS_HUMAN` with state left untouched and no strike recorded.
- [ ] The hard guards run before selection, ledger writes, branch changes, or dispatch: nesting under a Ralph harness refuses, and a tree dirty outside `.flow/` terminates with no cleanup and no claim reset.
- [ ] Verification evidence is echoed into the transcript — flowctl status fields, task counts and transitions, and for make-pr the gh-confirmed open PR URL — because the driver's validator reads output only.
- [ ] Under `--dry-run` the tick stops after classification: no ledger file created or modified, no branch checked out, nothing dispatched, and the root config snapshot removed before the verdict prints.
- [ ] Stage routing and work advancement decide through the satisfying set `{ship, not_required}`, never a bare `== ship` / `!= ship` check: a policy-excused spec is never re-routed to `work` and never logs a no-advance strike, while an unknown or unrecognized member satisfies nothing (fail closed).
- [ ] The tick re-reads the skill file at tick start (the file on disk is the contract, not the remembered copy), and an idle dispatched agent is probed read-only through its side effects — commits, receipts, status fields — never via a resume message. A tick executed from a stale in-context copy, or a resume sent to a merely-slow agent, has broken this.
- [ ] The no-plan route is entered only from the spec's own `no_plan` field (fn-214): the zero-task-plus-field classification row sits ahead of the default zero-task-to-plan row, the work dispatch appends `--no-plan` when that row matched, and pilot's parser accepts no `--no-plan` flag (a stray one gets the unknown-flag notice and the tick proceeds). A tick that inferred no-plan without the field, re-added the flag, or whose default zero-task row consumed a field-carrying spec, has broken this.
