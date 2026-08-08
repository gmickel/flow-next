# Conduct checklist — flow-next-export-context

A correct run builds RepoPrompt context for a plan or implementation review and exports it as one markdown file for an external model.

- [ ] The request is parsed into a type and target — `plan <spec-id>` gathers via `flowctl show` / `flowctl cat`, `impl` gathers the current branch, its commits, and its changed files.
- [ ] The prompt path is composed once as a literal unique path and typed verbatim in every block that touches it, never carried in a shell variable across tool calls.
- [ ] The builder handoff reaches the prompt file by redirection from `flowctl rp prompt-get`; the run never re-types or pastes that content. A run that reconstructs the handoff inside a heredoc has broken this.
- [ ] Only the static review criteria — the same criteria block as plan-review or impl-review, per export type — are typed, once, in the quoted heredoc appended to the prompt file.
- [ ] The run ends with `flowctl rp prompt-export` to a timestamped output file and tells the user that exact path plus what the file contains.
- [ ] The run stays manual-only: it declines an autonomous Ralph invocation rather than pretending to produce receipts or status updates.
