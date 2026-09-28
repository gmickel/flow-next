# Conduct checklist - /flow-next:features

A correct run seeds or maintains the committed user-POV map at `.flow/features/` and ends with a typed `FEATURES_VERDICT=` line.

- [ ] The last line of the run is exactly one `FEATURES_VERDICT=<SEEDED|CLEAN|CHANGED|BLOCKED|REFUSED> features=<n> reason="<one line>"` line, with nothing after it. A run that omits it, prints it mid-stream, or uses another verdict token has broken this.
- [ ] Doctor ran read-only before the first drive, on each fresh session, and again after any failed drive. A drive of an instance this run did not start, or a kill-by-process-name, has broken this.
- [ ] Every feature file that landed was proven by one live drive before it shipped. A cleanup that ate the evidence at its named path, or an undriven entry in the map, has broken this.
- [ ] On maintain, the staged diff is `.flow/features/**` plus harness scripts the map already owns, plus the memory files of drift notes whose route this pass re-proved. Product-code edits, or a product bug folded into the PR, have broken this.
- [ ] Every file whose route proved this pass carries a `**Last proven:**` line for that drive; a file whose route did not prove keeps its old line.
- [ ] `CHANGED` is one chore PR (opened through `${FLOW_PR_CREATE_CMD:-gh pr create} --body-file`, with a printed PR URL) whose body has Summary / What changed / Per-feature outcomes / Evidence pointers, never `/flow-next:make-pr`, never a merge. It is a pushed branch with no PR only when no create command reaches the host, and a local branch or uncommitted edits only when the user asked for less; the `reason` names which. Branch and commit follow the repo's naming rules. `CLEAN` has no branch and no PR.
- [ ] A commit, push, or PR-create failure after the proofs ends `BLOCKED` with the proven edits left in place and named; only a block before or during the proofs, or a moved base, restores them.
- [ ] Any autonomy-marker hit (`FLOW_RALPH*`, `REVIEW_RECEIPT_PATH`, `FLOW_*AUTONOM*`, `mode:autonomous`) ends `FEATURES_VERDICT=REFUSED` with no map writes.
