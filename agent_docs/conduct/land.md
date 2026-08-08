# Conduct checklist — /flow-next:land

A correct tick discovers the open PRs the build loop authored, walks each through the gate tree, takes at most one action class per PR, and ends on a single terminal verdict line.

- [ ] The last line of the response is exactly one `LAND_VERDICT=<verdict|NO_WORK> prs=<n> pr=<deciding-pr-url|-> reason="<one line>"`, computed by the worst-severity rule across PRs, with nothing printed after it.
- [ ] The tick asks the user nothing; ambiguity is reported as `NEEDS_HUMAN`. A tick that puts a question to the user has broken this.
- [ ] Each PR gets at most one action class, and its gate reads are echoed into the transcript — CI tri-state, patience window, unresolved threads, review signal — because the cadence driver is transcript-blind and reads nothing else.
- [ ] Only PRs carrying both authorship signals are mutated: the branch matches a spec's `branch_name` and the structural authorship probe finds the make-pr machine marker in footer position. Branch-only matches are reported `NEEDS_HUMAN` and left untouched.
- [ ] A merge happens only after every gate passes in-tick and uses `--squash --delete-branch --match-head-commit`; `gh pr merge --auto` and merge-queue enrollment never appear, and merge-conflict hunks are never hand-resolved.
- [ ] `--dry-run` produces full discovery plus per-PR classification and the aggregated terminal line with zero mutations — no checkout, push, label, merge, resolve-pr dispatch, or ledger write.
