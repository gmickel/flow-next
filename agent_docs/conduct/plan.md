# Conduct checklist — /flow-next:plan

A correct run turns a rough idea into a spec with right-sized tasks in `.flow/`, grounded in repo research — and writes no code.

- [ ] Every artifact is created or updated through `flowctl` into `.flow/`. A markdown TODO list, a TodoWrite call, or a plan file outside `.flow/` has broken this.
- [ ] The spec and task specs describe what, not how: signatures, repo patterns carried with `file:line` refs, and non-obvious gotchas only. A copy-paste-ready function body in a task spec has broken this. The `file:line` refs live in the task specs — a spec body stating file paths or line numbers instead of contracts has broken the durability rule.
- [ ] Step 1 launches the depth-appropriate scout set in one parallel call before any spec content is written; no scout in that set is skipped or run serially.
- [ ] New acceptance criteria carry R-IDs in the `- **Rn:** ...` prose form, each behavioral R-ID names its error and boundary cases, and existing R-IDs are never renumbered.
- [ ] Tasks are sized to fit a single `/flow-next:work` iteration, and the closing summary reports the validate result plus the derived execution waves.
- [ ] Under `mode:autonomous` no setup questions are asked — the autonomous defaults apply, and genuinely unanswerable input stops with a one-line `NEEDS_HUMAN:` report instead of a prompt.
- [ ] The interactive menu printed exactly one `Recommended next:` line above the numbered options; a skip-plan-review recommendation named one of the two ceremony shapes (docs/chore-class, or small-task-class with no design risk); `AUTONOMOUS=1` output carried no recommendation line.
- [ ] An empirically answerable fork the plan hinges on — a behavior, a timing, an output the running code can settle — is settled by a throwaway probe with the answer read back, never parked as an open question or put to the user — but only when the probe is non-mutating or fully disposable; a run that auto-executed a stateful or destructive command (a migration, a deployment, a write API) as a probe has broken this. A plan that asked the user for a fact the machine already held has broken this too, in the other direction.
- [ ] Wildly divergent independent inputs on one question (scout reports, review verdicts, consulted models) trigger a reframe-and-re-run of the question. A plan that averaged divergent opinions, or quietly picked the preferred one, has broken this.
- [ ] Every refactor-shaped task (restructuring without behavior change) names its equivalence harness in the task body — a script diffing old-vs-new outputs, or a recorded baseline replayed against the new code. A refactor task pinned only by "existing tests pass" when those tests never covered the moved behavior has broken this.
