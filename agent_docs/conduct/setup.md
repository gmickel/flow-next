# Conduct checklist — /flow-next:setup

A correct run detects the host platform, initializes `.flow/`, asks only the still-unanswered configuration questions in one grouped prompt, writes marker-bounded docs snippets, and stamps the setup mode before printing a summary.

- [ ] The platform is resolved from the host's own signals in the documented precedence, and every downstream choice matches it — a Cursor or Grok repo that received the Codex `$flow-next-` snippet, or a Codex install misclassified as Cursor through an inherited env var, has broken this.
- [ ] Configuration questions are built only from keys that read raw-null in `.flow/config.json`, so a re-run with everything set asks nothing it already knows and silently flips no earlier answer.
- [ ] Docs snippets are written through `flowctl setup-block apply`, touching only the bytes inside the flow-next markers; an `ask` result prompts Keep mine / Overwrite / abort rather than replacing a customized block.
- [ ] User-owned files — repo-root `SPEC.md`, `.flow/usage.md`, `.flow/criteria.md` — are compared before writing, left untouched when identical, and never overwritten without an explicit answer.
- [ ] Under any autonomy marker (`FLOW_RALPH`, `REVIEW_RECEIPT_PATH`, `FLOW_AUTONOMOUS`, `mode:autonomous`) the Ralph, model-routing, and model-pin ceremonies are skipped silently instead of blocking on a question.
- [ ] The run stamps exactly one setup mode via `flowctl setup-mode set`, and a refused plugin stamp materializes the copy-mode files before stamping copy — a completed run never leaves `setup_mode` unset.
