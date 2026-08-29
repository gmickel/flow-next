# Conduct checklist - /flow-next:features

A correct run seeds or maintains the committed user-POV map at `.flow/features/` and ends with a typed `FEATURES_VERDICT=` line.

- [ ] The last line of the run is exactly one `FEATURES_VERDICT=<SEEDED|CLEAN|CHANGED|BLOCKED|REFUSED> features=<n> reason="<one line>"` line, with nothing after it. A run that omits it, prints it mid-stream, or uses another verdict token has broken this.
- [ ] Doctor ran read-only before the first drive, on each fresh session, and again after any failed drive. A drive of an instance this run did not start, or a kill-by-process-name, has broken this.
- [ ] Every feature file that landed was proven by one live drive before it shipped. A cleanup that ate the evidence at its named path, or an undriven entry in the map, has broken this.
- [ ] On maintain, the staged diff is `.flow/features/**` plus harness scripts the map already owns. Product-code edits, or a product bug folded into the PR, have broken this.
- [ ] `CHANGED` is one chore PR (`gh pr create --body-file`) whose body has Summary / What changed / Per-feature outcomes / Evidence pointers, never `/flow-next:make-pr`, never a merge. `CLEAN` has no branch and no PR.
- [ ] Any autonomy-marker hit (`FLOW_RALPH*`, `REVIEW_RECEIPT_PATH`, `FLOW_*AUTONOM*`, `mode:autonomous`) ends `FEATURES_VERDICT=REFUSED` with no map writes.
