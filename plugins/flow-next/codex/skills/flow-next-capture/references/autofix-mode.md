# capture — autofix mode (loaded on demand)

> Loaded ONLY when `$ARGUMENTS` carried the literal token `mode:autofix`. The default
> interactive run never reads this file.

## Autofix mode rules

- **No user questions.** Never call the plain-text numbered prompt.
- **Phase 0 hard-errors:** duplicate detected → list overlapping spec IDs to stderr, exit 2 unless `--rewrite <id>` was passed; relevant capture evidence is missing / truncated / summary-only after compaction → exit 2 unless `--from-compacted-ok` was passed. A historical compaction marker or system-summary block alone is advisory and does not block.
- **Phase 3 must-ask hard-errors:** ambiguous title / untestable acceptance / scope-conflict-with-existing-spec → exit 2 with which case fired and why. Autofix cannot resolve must-ask cases.
- **Phase 4 single emission, no `.flow/` write.** Full draft Written once to the §4.1 draft file (all sections + R-IDs); summary payload (`[inferred]` tally + 8+ acceptance suggestion if applicable) printed to stdout. Without `--yes`, exit 0 with the "rerun with --yes" hint. With `--yes`, proceed to Phase 5 write. (Autofix has no interactive print-then-ask; `--yes` is the consent substitute.)
- **Phase 5 commits identically to interactive once it runs.**
- **Readiness never written.** The mark-ready write (workflow.md §5.9) is interactive-consent-only; autofix prints a footer suggestion at most (and only when readiness is adopted, no `tracker.readyState`, and the spec was written). The `--rewrite` readiness reset (§5.3) still runs — it is idempotent plumbing, not a consent question.

## 4.4 — Autofix read-back

Autofix paths are unchanged by the interactive print-then-ask contract (no user to ask). The §4.1 Write materializes the draft file; print the **summary payload** (§4.1 items — tally, 8+ note, related memory, rewrite diff, glossary suggestions) to stdout. Then:

- If `COMMIT_YES=0`, exit 0 with: `Draft written to <literal draft path> (content in the Write render above). Re-run with --yes to commit (in autofix mode, --yes substitutes for the interactive read-back approval).`
- If `COMMIT_YES=1`, proceed to Phase 5.

Autofix never offers `edit` — there's no user to ask. The Write + `--yes` pattern mirrors `flowctl memory migrate --yes` and is the documented autofix-substitute for read-back approval.

**Autofix + split proposal:** autofix never multiplies artifacts. When Phase 2.5 proposed N>1, autofix writes ONE spec and records the proposal inside it — `## Decision Context` gains an `### Split proposal (unactioned)` H3 carrying the per-spec titles, criteria allocation, and edges — plus a one-line stdout note: `Split proposal (N specs) recorded in Decision Context — act on it via /flow-next:interview <id> or manual spec create + add-dep.`

**Autofix + glossary proposals:** the summary payload's glossary block prints as suggestions (`Suggested glossary adds — review and add via flowctl glossary add "<term>" --definition-file -`), but autofix **never writes terms** — not even with `--yes` (`--yes` consents to the spec write, not to vocabulary changes). Phase 5.8 is interactive-only.

**Autofix + no-plan (fn-214, R5):** the spec-level `no_plan` field is written in autofix **only** when the invocation carried the explicit `--no-plan` flag AND the spec was written (`--yes`) — §5.9b runs identically to interactive then (it is flag-consent, not a question). Without the flag the field is never set: autofix never infers no-plan from the draft or the conversation.

**Autofix + readiness:** autofix **never writes readiness** — not even with `--yes` (Phase 5.9 is interactive-only). When the §4.2 target-aware predicate yields `READY_OFFER=true` AND the spec gets written (`--yes`), Phase 6 appends a one-line suggestion: `Mark ready when blessed: flowctl spec ready <SPEC_ID>`. Without `--yes` nothing is suggested (no spec id exists). Predicate fails → silence — including non-adopters, tracker-authoritative repos, and draft rewrite targets made visible only by an unrelated ready spec.

## Autofix exit summary

In autofix mode, every "ask" branch becomes "exit 2". Capture cannot guess on must-ask cases. Glossary term-adds are never written in autofix — proposals print as suggestions only.

In autofix without `--yes`, the draft is Written and the skill exits 0 — no `.flow/` write, no spec allocated.
In autofix with `--yes`, the §4.1 Write + `--yes` substitutes for the interactive print-then-ask approval before Phase 5 writes.
