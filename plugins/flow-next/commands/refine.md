---
name: refine
description: Refine a spec, task, or spec file in-depth - question passes (business, technical, both) or a read-only research pass
argument-hint: "[spec ID, task ID, or file path] [--scope=business|technical|both|research | --biz | --tech] [--docs | --no-docs] [--strategy | --no-strategy] [--force]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-refine`

The ONLY purpose of this command is to call the `flow-next-refine` skill. You MUST use that skill now.

**User input:** $ARGUMENTS

Pass the user input to the skill. The skill handles the question passes and the research pass. `/flow-next:interview` is the deprecated alias for one release.

## Optional flags

### Scope (added in 1.1.0)

- `--scope=technical` (default) — runs the technical pass only. Writes tech-owned sections (`Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`, verifiable acceptance criteria). Preserves any populated business sections byte-for-byte. Reads business sections when present and cites them in the opener; silent when absent. This IS the 1.0.2 single-pass behavior — preserving as default means zero breaking change for solo devs.
- `--scope=business` — runs the business pass only. Writes biz-owned sections (`Goal & Context`, `Boundaries`, `### Motivation` under `## Decision Context`, outcome acceptance criteria). Preserves technical-section bodies byte-for-byte; writes placeholder `*Pending technical-scope interview pass.*` ONLY under empty tech sections. BEFORE drafting biz questions, runs a project-docs investigation (`README.md`, `CHANGELOG.md`, `STRATEGY.md`, `GLOSSARY.md`, `knowledge/decisions/`, `.flow/specs/` index, `docs/`); items resolved by docs land in `## Resolved via Project Docs` and the user is NOT asked about things the project docs already define.
- `--scope=both` — runs the business pass first, then the technical pass in the same skill invocation. Same merge contract applies in each phase; auxiliary sections preserved across both.
- `--biz` — short alias for `--scope=business`.
- `--tech` — short alias for `--scope=technical`.
- `--scope=research` — runs no questions. Dispatches the read-only docs, practice, docs-gap, and memory scouts (github when `scouts.github` is on) over the spec's or task's surface and writes a `## Resolved via Research` section (one sub-block per scout: library versions, changed APIs, gotchas, docs that must change, memory that applies, each with its source) through the same read-back approval. Observably skipped, with the reason printed and nothing written, when the section already exists or plan's scout findings are already on the spec's tasks; `--force` reruns it; a spec that now names a library the plan never saw reruns it scoped to that delta.

Conflicting flags (`--biz --tech`, `--scope=business --tech`, `--scope=foo`) error cleanly with an explicit "conflicting scope flags" or "invalid --scope value" message. R-IDs in `## Acceptance Criteria` are append-only across scope passes — never renumbered, never replaced.

### Doc-aware (existing)

- `--docs` — force doc-aware mode on. The interview reads the nearest-ancestor `GLOSSARY.md` and `.flow/memory/knowledge/decisions/`, surfaces glossary conflicts, sharpens overloaded terms via `flowctl glossary add`, and writes decision entries via `flowctl memory add --track knowledge --category decisions ...` when the three-criteria gate passes. If no `GLOSSARY.md` exists yet, the first resolved term lazy-creates one at the repo root.
- `--no-docs` — force doc-aware mode off, even when `GLOSSARY.md` or decision entries exist.
- `--strategy` / `--no-strategy` — force the strategy-aware gate independently of `--docs` / `--no-docs`. Without an explicit flag, `--docs` / `--no-docs` cascades to strategy.

Without any doc-aware flag, the mode autodetects: it activates when `GLOSSARY.md` has at least one defined term (`flowctl glossary list --json` reports `total_terms > 0`) OR `.flow/memory/knowledge/decisions/` has at least one entry OR `STRATEGY.md` has populated sections. An empty `# Glossary` husk left behind after the last term is removed does not trip autodetect.

The `--scope` axis is orthogonal to doc-aware — both can be combined freely (e.g., `--scope=business --docs` runs the biz pass with doc-aware behaviors layered on).

Examples:

- `/flow-next:refine fn-1-add-oauth` — default `--scope=technical`, autodetect doc-aware (the 1.0.2 behavior, unchanged)
- `/flow-next:refine fn-1-add-oauth --biz` — business pass; project-docs investigation runs first; writes biz sections only, placeholders under empty tech sections
- `/flow-next:refine fn-1-add-oauth --scope=both` — biz pass then tech pass in one invocation; tech pass reads biz output as context
- `/flow-next:refine fn-1-add-oauth --scope=business --docs` — biz pass with explicit doc-aware mode (glossary + decisions + strategy gates all on)
- `/flow-next:refine fn-1-add-oauth --no-docs` — force doc-aware off (scope defaults to technical)
- `/flow-next:refine fn-1-add-oauth --scope=research` — external-docs pass; no questions; skipped when the section or plan's findings already exist
- `/flow-next:refine fn-1-add-oauth --scope=research --force` — rerun the external-docs pass and replace the section
