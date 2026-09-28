---
name: refine
description: Refine a spec, task, or spec file - one question pass that asks only what would change the build, optionally focused by a free-text scope lens, or a read-only research pass
argument-hint: "[spec ID, task ID, or file path] [--scope=<lens> | --scope=research | --biz | --tech] [--docs | --no-docs] [--strategy | --no-strategy] [--force]"
disable-model-invocation: true
---

# IMPORTANT: This command MUST invoke the skill `flow-next-refine`

The ONLY purpose of this command is to call the `flow-next-refine` skill. You MUST use that skill now.

**User input:** $ARGUMENTS

Pass the user input to the skill. The skill handles the interview and the research pass.

## Optional flags

### Scope

- `--scope=<lens>` — optional free-text lens: `business`, `technical`, `qa`, `security`, or any other audience. Refine runs one interview either way; the lens focuses the questions on that audience's decisions, and each answer is written to the section it belongs in. No lens means no filter, and refine never asks which scope to run.
- `--biz` — alias for `--scope=business`.
- `--tech` — alias for `--scope=technical`.
- `--scope=research` — runs no questions. Dispatches the read-only docs, practice, docs-gap, and memory scouts (github when `scouts.github` is on) over the spec's or task's surface and writes a `## Resolved via Research` section (one sub-block per scout: library versions, changed APIs, gotchas, docs that must change, memory that applies, each with its source) through the same read-back approval. Observably skipped, with the reason printed and nothing written, when the section already exists or plan's scout findings are already on the spec's tasks; `--force` reruns it; a spec that now names a library the plan never saw reruns it scoped to that delta.

Sections no answer belongs in come back byte-for-byte, and the read-back names every section the session changed. R-IDs in `## Acceptance Criteria` are append-only — never renumbered, never replaced.

### Doc-aware

- `--docs` — force doc-aware mode on. The pass reads the nearest-ancestor `GLOSSARY.md` and `.flow/memory/knowledge/decisions/`, surfaces glossary conflicts, sharpens overloaded terms via `flowctl glossary add`, and writes decision entries via `flowctl memory add --track knowledge --category decisions ...` when the three-criteria gate passes. If no `GLOSSARY.md` exists yet, the first resolved term lazy-creates one at the repo root.
- `--no-docs` — force doc-aware mode off, even when `GLOSSARY.md` or decision entries exist.
- `--strategy` / `--no-strategy` — force the strategy-aware gate independently of `--docs` / `--no-docs`. Without an explicit flag, `--docs` / `--no-docs` cascades to strategy.

Without any doc-aware flag, the mode autodetects: it activates when `GLOSSARY.md` has at least one defined term (`flowctl glossary list --json` reports `total_terms > 0`) OR `.flow/memory/knowledge/decisions/` has at least one entry OR `STRATEGY.md` has populated sections. An empty `# Glossary` husk left behind after the last term is removed does not trip autodetect.

The scope lens is orthogonal to doc-aware — both combine freely (e.g., `--scope=business --docs`).

Examples:

- `/flow-next:refine fn-1-add-oauth` — one interview, no lens, autodetect doc-aware
- `/flow-next:refine fn-1-add-oauth --biz` — the same interview, focused on the product owner's decisions
- `/flow-next:refine fn-1-add-oauth --scope=qa` — focused on what QA decides (what counts as done, which failures matter)
- `/flow-next:refine fn-1-add-oauth --scope=business --docs` — business lens with doc-aware mode forced on
- `/flow-next:refine fn-1-add-oauth --no-docs` — force doc-aware off
- `/flow-next:refine fn-1-add-oauth --scope=research` — external-docs pass; no questions; skipped when the section or plan's findings already exist
- `/flow-next:refine fn-1-add-oauth --scope=research --force` — rerun the external-docs pass and replace the section
