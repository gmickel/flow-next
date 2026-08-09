# Conduct checklist — /flow-next:plan

A correct run turns a rough idea into a spec with right-sized tasks in `.flow/`, grounded in repo research — and writes no code.

- [ ] Every artifact is created or updated through `flowctl` into `.flow/`. A markdown TODO list, a TodoWrite call, or a plan file outside `.flow/` has broken this.
- [ ] The spec and task specs describe what, not how: signatures, repo patterns carried with `file:line` refs, and non-obvious gotchas only. A copy-paste-ready function body in a task spec has broken this. The `file:line` refs live in the task specs — a spec body stating file paths or line numbers instead of contracts has broken the durability rule.
- [ ] Step 1 launches the depth-appropriate scout set in one parallel call before any spec content is written; no scout in that set is skipped or run serially.
- [ ] New acceptance criteria carry R-IDs in the `- **Rn:** ...` prose form, each behavioral R-ID names its error and boundary cases, and existing R-IDs are never renumbered.
- [ ] Tasks are sized to fit a single `/flow-next:work` iteration, and the closing summary reports the validate result plus the derived execution waves.
- [ ] Under `mode:autonomous` no setup questions are asked — the autonomous defaults apply, and genuinely unanswerable input stops with a one-line `NEEDS_HUMAN:` report instead of a prompt.
