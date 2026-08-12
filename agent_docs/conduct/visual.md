# Conduct checklist — /flow-next:visual

A correct run restates ONE target (spec, task, diff, or the current topic) as a compact markdown digest that fits one screen, grounded entirely in state it actually read, and writes nothing.

- [ ] The reply is a digest, not an essay: one screen, no preamble, no prose restatement of the spec. A spec post-plan digest carries the six elements in order — thesis, task tree, planned file-layout diff, shape sketch (or an explicit skip), R-ID coverage line, boundaries.
- [ ] Every path in a file tree and every edge in a call tree traces to something read in the transcript — a task file, the spec, `git diff --stat`, or code opened this session. One invented path, node, or "for clarity" edge breaks this.
- [ ] The R-ID coverage line is derived from the tasks' declared `satisfies` frontmatter (read per task with `flowctl cat`) checked against the spec's R-IDs, not re-narrated from spec prose, and uncovered R-IDs are shown as `UNCOVERED` rather than omitted.
- [ ] A one-or-two-sentence plain statement precedes every visual, and the run uses one or a few shapes chosen for the question — never a tour of all eight.
- [ ] No mermaid is emitted when a text shape would have carried the same point; a mermaid block appears only for genuine interaction/sequence, and then as sequence or state.
- [ ] The run is read-only: no Write or Edit tool use, no state-mutating flowctl subcommand, no commit, no other workflow invoked. Missing state degrades to the nearest viable mode with a one-line notice of what was unavailable, instead of a fabricated digest.
