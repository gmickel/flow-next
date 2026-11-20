# Conduct checklist — /flow-next:setup

A correct run detects the host platform, initializes `.flow/`, asks only the still-unanswered configuration questions in grouped prompts, writes marker-bounded docs snippets, and offers to delete leftover copies from older installs before printing a summary.

- [ ] The platform is resolved from the host's own signals in the documented precedence, and every downstream choice matches it — a Cursor or Grok repo that received the Codex `$flow-next-` snippet, or a Codex install misclassified as Cursor through an inherited env var, has broken this.
- [ ] Configuration questions are built only from keys that read raw-null in `.flow/config.json`, so a re-run with everything set asks nothing it already knows and silently flips no earlier answer.
- [ ] Docs snippets are written through `flowctl setup-block apply`, touching only the bytes inside the flow-next markers; an `ask` result prompts Keep mine / Overwrite / abort rather than replacing a customized block. On a host that reads `AGENTS.md`, a saved Docs answer that leaves `AGENTS.md` out while the host cannot see `CLAUDE.md` writes no `AGENTS.md` and the summary says the host will not see the snippet.
- [ ] Nothing is copied into `.flow/` (no `.flow/bin/`, `.flow/templates/spec.md`, or `.flow/usage.md`). User-owned files — repo-root `SPEC.md`, `.flow/criteria.md` — are compared before writing, left untouched when identical, and never overwritten without an explicit answer.
- [ ] Under any autonomy marker (`FLOW_AUTONOMOUS`, `AUTONOMOUS=1`, `mode:autonomous`) the run asks nothing: optional questions are deferred and the model-routing block is not written.
- [ ] Leftover copies from an older install are listed and deleted only on an explicit `Delete them` answer (a customized `.flow/templates/spec.md` is excluded), and the closing summary states that plugin updates need no setup re-run.
