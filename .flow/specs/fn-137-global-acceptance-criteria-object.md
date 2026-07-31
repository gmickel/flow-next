# Global acceptance criteria object

## Goal & Context
<!-- scope: business -->

Projects accumulate standing, project-wide acceptance criteria - "every route change regenerates the contract", "no new dependency without a health check", "user-facing strings live in the i18n catalog" - that today live in CLAUDE.md prose and reviewer memory. MergeFoundry MASTERPLAN decision 6 (binding): NOT a separate auditor fleet - a lightweight flow-next-native criteria object that the EXISTING completion-review skill applies agentically to every spec, with compliance landing in ordinary receipts. Lean on agents: the criteria are prose judged by the reviewer that already runs; no new engine, no scoring math.

## Scope
<!-- scope: technical -->

- The object: `.flow/criteria.md` - a plain markdown file of numbered global criteria (`- **G1:** ...` mirroring R-ID grammar with a G- prefix; optional per-criterion scope hint like paths/globs in prose). Setup offers to scaffold it (opt-in, like other setup artifacts); absence changes nothing anywhere.
- flowctl plumbing (thin): `flowctl criteria list --json` (parse + validate ids/uniqueness); no judgment in flowctl.
- Skill integration (completion-review, all backends): when `.flow/criteria.md` exists, the review prompt includes the criteria block and the reviewer verdict must address them; per-criterion compliance (met / violated w/ finding / not-applicable) lands in the receipt as `criteria: [{id, status, note?}]` - parsed deterministically by extending the landed fn-136 findings-parser infrastructure. Gate-level application (work full gate or any future gate skill) is deferred downstream; completion review is the sole compliance surface in this spec.
- Prompt-diet discipline: the criteria block is user content (their criteria file), not skill prose; the skill delta is the small instruction to apply it - measured, bounded, and gated behind file existence so criteria-less repos pay no criteria content in assembled prompts.
- Receipts schema addition is additive/optional; docs (memory-schema, teams.md mention, setup docs); sync-codex pass.

## Boundaries / non-goals

- NO auditor fleet, no separate audit pass, no deterministic rule engine, no scoring.
- NO per-task criteria application (completion review / gate level only - the spec is the unit of compliance).
- Criteria authoring UX beyond the setup scaffold is downstream (MergeFoundry renders compliance; a criteria editor is not flow-next's job).
- No changes to plan/work skills.

## Acceptance Criteria

- **R1:** `.flow/criteria.md` with G-ID grammar parses via `flowctl criteria list --json` (validation: unique ids, non-empty); absence is a silent no-op everywhere - the assembled review prompt contains no criteria content when the file is absent (tested by prompt-assembly inspection); skill-prose delta bounded per R4.
- **R2:** Completion-review (all backends) includes existing criteria in the review and receipts carry per-criterion compliance `criteria: [{id, status, note?}]` parsed deterministically; unparseable compliance degrades to absent, never an error.
- **R3:** Setup offers the scaffold opt-in; scaffolded template documents the grammar with examples; declining leaves no trace.
- **R4:** Skill prose deltas measured and bounded (criteria instruction gated on file existence); sync-codex idempotent; no new LLM calls.
- **R5:** Docs updated (setup, memory-schema/receipts, a teams.md note on standing criteria); the G-ID grammar documented beside the R-ID grammar.
