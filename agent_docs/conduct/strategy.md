# Conduct checklist — /flow-next:strategy

A correct run produces or maintains `STRATEGY.md` at the repo root — the durable anchor for target problem, approach, who it's for, key metrics, and tracks — by asking sharp questions and pushing back on weak answers.

- [ ] The run classifies file state from `flowctl strategy status --json` before writing anything, and announces the selected path (`Strategy doc not found — let's write it.` or `Found existing strategy — let's review and update.`). A session that starts interviewing without a classification read has broken this.
- [ ] Exactly one workflow reference is loaded for the selected route — `references/first-run.md` or `references/update.md`, never both.
- [ ] A `STRATEGY.md` with `generator_match: false` is left unchanged unless the user confirms a destructive rewrite through the two-step Boundaries question; the transcript shows the ask, not a silent overwrite.
- [ ] Substantive sections (target problem, approach, persona, metrics, tracks) are asked free-form with no recommendation and no menu; lead-with-recommendation appears only on routing questions.
- [ ] Each section is captured in at most two rounds, and a section that ends on round two carries the `<!-- worth revisiting -->` marker in the written file.
- [ ] The run ends with the `flowctl strategy read --json` read-back, the draft shown in chat, and a single-paragraph downstream handoff naming the skills that read the doc — no extra exit summary. A run under Ralph exits 2 instead of writing at all.
