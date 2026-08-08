# Conduct checklist — /flow-next:interview

A correct run extracts complete implementation details through deep questioning in rounds, then writes the refined spec, task, or file back under the resolved scope's write policy.

- [ ] Every question goes through the blocking question tool, and each body carries a stakes sentence, a named recommendation with its rationale, and one confidence tier — `[high]`, `[judgment-call]`, or `[your-call]`. A transcript that prints "Question 1: ..." as plain narration has broken this.
- [ ] Each round asks the whole current frontier and never pairs a question with its own prerequisite; when an answer prunes a sub-tree, the next round's opener names the abandoned branch.
- [ ] Codebase- and project-docs-answerable questions are resolved by investigation and logged under `## Resolved via Codebase` or `## Resolved via Project Docs` with file:line or path evidence, instead of being put to the user. A "should we" question answered by grep has broken this too, in the other direction.
- [ ] Skipped questions land under `## Open Questions` with the unconfirmed leaning and an owner hint, and the agent's recommendation is never written into a spec section as decided content; with one or more skips, the write-back consent checkpoint is asked before the spec is written.
- [ ] The write-back honors the `flowctl scope write-policy` result: sections the pass does not own and the auxiliary sections come back byte-for-byte, and acceptance-criteria R-IDs are appended with source tags, never renumbered or replaced.
- [ ] The completion summary reports the question count, the skip disposition when there were skips, which scope pass or passes ran, and which sections were written versus preserved.
