# Conduct checklist — /flow-next:capture

A correct run synthesizes the conversation into a source-tagged spec, reads the full draft back, and only then writes it via `flowctl spec create` + `spec set-plan`.

- [ ] The full draft is materialized once to a literal draft path and, in interactive mode, printed as ordinary markdown before a short approval ask. An ask body carrying the multi-paragraph draft, the diff, or the criteria list has broken this.
- [ ] No write into `.flow/` happens before approval — `flowctl spec create` appears after the approve, and `spec set-plan <id> --file <literal draft path>` consumes the draft file instead of a re-authored heredoc.
- [ ] Acceptance criteria capture newly authors carry `[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]` tags, and the read-back does not recommend `approve` while unverified `[inferred]` items remain.
- [ ] Chart, B-ID, cluster, D-ID, and approved-asset evidence appears as links and references in the evidence sections without trailing source tags, and `flowctl chart link-spec` is called only after a successful create + set-plan.
- [ ] Refusal conditions fire rather than being worked around: an existing spec without `--rewrite`, a draft or stale briefing without a named-D-ID risk override, and a Ralph environment (`FLOW_RALPH` / `REVIEW_RECEIPT_PATH`) all stop the run.
- [ ] The commit stages only `.flow/specs/<id>.md`, its JSON sidecar, and `.flow/meta.json` when the counter moved. A run that reaches for `git add -A` has broken this.
