# Conduct checklist — /flow-next:make-pr

A correct run renders a cognitive-aid PR body from flow-next state and opens the PR via `gh`, so a human can decide where to focus before skimming the diff.

- [ ] Every claim in the body traces to a field of the `flowctl spec export-cognitive-aid` payload — file paths from `diff.files`, SHAs from task evidence, "why" from `memory.decisions[]`, findings from `reviews.*` — or, for the orphaned-evidence marking alone, to the warnings of the one bounded `flowctl validate --spec` call Phase 1 makes (fn-180). Missing data is stated honestly rather than narrated into a plausible-sounding rationale.
- [ ] The structured PR cognitive aid runs on every invocation, including `--dry-run`, and its rendered walkthrough is what the body carries in place of the legacy Verification section - and of the R-ID coverage table only when coverage is fully evidenced; with any unevidenced or undeclared criterion that table renders beside the walkthrough (fn-180).
- [ ] The PR is created without a confirm gate; the only questions asked are the Phase 0 info prompts for something that cannot be derived, such as an unresolvable base ref or undetected spec id. A run that asks "do you want to create it?" has broken this.
- [ ] `--dry-run` puts the body on stdout and stops before any `git push`, `gh pr create`, or artifact commit.
- [ ] Undeclared R-IDs (no task claims them) are flagged rather than attributed to a task; claimed-but-not-evidenced criteria keep their claiming-task attribution with the claimed-not-evidenced marker (fn-180). The body describes the diff without quoting raw code from it.
- [ ] A created PR ends with the breadcrumb line and the `<!-- flow-next:make-pr spec=<spec-id> base=<base-ref> -->` machine marker in footer position, which land's authorship probe keys on.
