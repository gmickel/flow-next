# capture — manual smoke (maintainer validation, not part of a run)

> Maintainer-facing. A capture session never needs this file; it is the manual validation
> description for prose changes to the skill.

## Manual smoke (acceptance R3, R4, R5, R6, R7, R8, R24, R25)

The skill itself is markdown — there's no unit-test surface. The validation is invoking `/flow-next:capture` in a real session. Expected behavior:

- Phase 0 walks `.flow/specs/`, runs memory search if memory is initialized, detects compaction, applies idempotency. Branches into duplicate-detection question if ≥2 strong matches; exits cleanly on `abort`.
- Phase 1 emits a `## Conversation Evidence` block with verbatim user quotes (≤30 lines).
- Phase 2 produces a draft with per-line source tags. Every acceptance criterion has one of `[user]` / `[paraphrase]` / `[inferred]`. Biz-context signals (R24) route to their destinations using only `[user]` / `[paraphrase]` tags; categories without conversation signal leave their destinations absent. `BIZ_SIGNAL_CATEGORIES` (0..9) computed for Phase 6.
- Phase 3 fires must-ask cases only when (a) title is genuinely ambiguous, (b) acceptance is untestable, (c) scope-conflict persists. Optional ambiguities are deferred to Phase 4.
- Phase 4 materializes the draft ONCE via the Write tool to a literal unique path (§4.1), then **print-then-ask** (interactive): prints the FULL draft markdown (and rewrite diff when applicable) as an ordinary assistant message, then a SHORT `AskUserQuestion` (one-line pointer + `[inferred]` tally/warnings + options only — never multi-paragraph drafts/diffs/criteria lists in the ask body). Interactive: user picks approve / edit / abort; edit cycles revise via the Edit tool + full-file Read + **reprint the revised draft** before each short re-ask; on approve with proposals, one follow-up `Glossary?` consent question; on approve with `READY_OFFER=true`, one follow-up `Mark ready?` consent question (default keep-draft). New captures set `READY_OFFER` only when ≥1 spec is ready and no `tracker.readyState` is configured; rewrites set it only when the target itself was ready and no `tracker.readyState` is configured. Autofix: Write + summary payload printed + require `--yes` (unchanged; no interactive ask); proposals print as suggestions, never written; readiness never written.
- Phase 5 calls `flowctl spec create` + `spec set-plan --file <literal draft path>` (consumes the §4.1 draft file — no heredoc re-authoring). Approved term-adds written via `flowctl glossary add` (5.8, interactive only). Consented mark-ready written via `flowctl spec ready` (5.9, interactive only). Rewrite branch (5.3) runs idempotent `spec unready` unconditionally; `READY_RESET` gates the Phase 6 announcement. With no glossary (or a husk), 2.7/4.x/5.8 are silent no-ops; with readiness un-adopted, 4.2's mark-ready question / 5.9 / all readiness footer lines are silent no-ops — zero behavior change. With `artifacts.html.enabled` true, 5.10 regenerates `.flow/artifacts/<id>/spec.html` per the disclosure reference and leaves exactly one `<!-- flow-next:artifact-link -->` line in the spec md; off/unset, 5.10 is a single config read and nothing else.
- Phase 6 prints the next-step footer. Agent-judges the R25 threshold (`1 <= BIZ_SIGNAL_CATEGORIES < 3`); on fire, appends the `/flow-next:interview --scope=business` suggestion line. R22 invariant: `BIZ_SIGNAL_CATEGORIES=0` → no-fire → no suggestion.

The two autofix end-states (`--yes` absent vs present) are stated once in [autofix-mode.md](autofix-mode.md) § Autofix exit summary — smoke both against that wording.

The Ralph-block (SKILL.md) ensures this skill never runs under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` — capture requires a user at the terminal.
