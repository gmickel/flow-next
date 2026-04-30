---
satisfies: [R11]
---

## Description

Extend the `docs-gap-scout` agent to scan `GLOSSARY.md` (root + subdirectories) and `.flow/memory/knowledge/decisions/` entries during planning. When a planned change touches a defined term or invalidates a decision constraint, the scout flags those targets in its output.

**Size:** S
**Files:** `plugins/flow-next/agents/docs-gap-scout.md`, regenerate Codex mirror via `scripts/sync-codex.sh`

## Approach

- Update the doc-location scan list at `docs-gap-scout.md:39` to include:
  - `GLOSSARY.md` (root) — direct check; prefer `flowctl glossary list --json` (JSON shape per fn-38.2: `{groups: [{path, entries, count}], file_count, total_terms}`) since it walks ancestors and respects gitignore conventions; raw `find` only as fallback. Empty husks (`count: 0` after last-term-removal — fn-38.2 keeps the file per R18) carry no terms — skip them, don't flag as drift signal. <!-- Updated by plan-sync: fn-38.2 shipped `glossary list --json` + husk semantics -->
  - Subdirectory `GLOSSARY.md` — covered by `glossary list --json` (walks ancestors); raw fallback `find . -name GLOSSARY.md -not -path './node_modules/*' -not -path './.git/*'`
  - `.flow/memory/knowledge/decisions/` — direct directory check
- Extend the change-type → doc-update mapping (`docs-gap-scout.md:59-68`) with two new rows:
  - **"Glossary term touched"** — when the planned-change diff modifies code that uses a term defined in any `GLOSSARY.md`, flag the glossary entry (file + term name) for review
  - **"Decision constraint"** — when the planned-change touches a file referenced in a decision entry's `Consequences` section, flag the decision entry (id + title) for review
- Run `scripts/sync-codex.sh` to regenerate `plugins/flow-next/codex/agents/docs-gap-scout.toml`. Verify the Codex mirror picks up the changes (no `AskUserQuestion` / DDD-jargon validator failures).
- **R17 compliance**: do NOT use DDD terminology in agent prose.

## Investigation targets

**Required:**
- `plugins/flow-next/agents/docs-gap-scout.md:39` — current scan list
- `plugins/flow-next/agents/docs-gap-scout.md:59-68` — change-type → doc-update mapping table
- `plugins/flow-next/codex/agents/docs-gap-scout.toml` — Codex mirror (auto-regen)

## Acceptance

- [ ] `docs-gap-scout` scan list includes `GLOSSARY.md` (root + subdirs via `find`) and `.flow/memory/knowledge/decisions/`
- [ ] Mapping table has rows for "Glossary term touched" and "Decision constraint" change-types
- [ ] `scripts/sync-codex.sh` regenerates `codex/agents/docs-gap-scout.toml` cleanly
- [ ] No DDD jargon in agent prose (R17 — manually verify; T7 grep guard catches regressions)
- [ ] Manual smoke: invoke `docs-gap-scout` on a planned change touching a glossary-defined term; verify glossary entry surfaces in scout output

## Done summary

## Evidence
