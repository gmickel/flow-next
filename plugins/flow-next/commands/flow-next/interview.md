---
name: flow-next:interview
description: Interview & refine a spec, task, or spec file in-depth
argument-hint: "[spec ID, task ID, or file path] [--docs | --no-docs]"
---

# IMPORTANT: This command MUST invoke the skill `flow-next-interview`

The ONLY purpose of this command is to call the `flow-next-interview` skill. You MUST use that skill now.

**User input:** $ARGUMENTS

Pass the user input to the skill. The skill handles the interview logic.

## Optional flags

- `--docs` — force doc-aware mode on. The interview reads the nearest-ancestor `GLOSSARY.md` and `.flow/memory/knowledge/decisions/`, surfaces glossary conflicts, sharpens overloaded terms via `flowctl glossary add`, and writes decision entries via `flowctl memory add --track knowledge --category decisions ...` when the three-criteria gate passes. If no `GLOSSARY.md` exists yet, the first resolved term lazy-creates one at the repo root.
- `--no-docs` — force doc-aware mode off, even when `GLOSSARY.md` or decision entries exist.

Without either flag, doc-aware mode autodetects: it activates when `GLOSSARY.md` has at least one defined term (`flowctl glossary list --json` reports `total_terms > 0`) OR `.flow/memory/knowledge/decisions/` has at least one entry. An empty `# Glossary` husk left behind after the last term is removed does not trip autodetect.

Examples:

- `/flow-next:interview fn-1-add-oauth` — autodetect doc-aware mode
- `/flow-next:interview fn-1-add-oauth --docs` — force doc-aware on
- `/flow-next:interview fn-1-add-oauth --no-docs` — force doc-aware off
