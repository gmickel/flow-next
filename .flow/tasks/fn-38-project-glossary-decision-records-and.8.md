## Description

Update all in-scope contributor docs to reflect the new glossary, decisions category, and doc-aware interview mode. Per CLAUDE.md "Contributing / Development" section: in-scope = CHANGELOG.md, plugins/flow-next/README.md, CLAUDE.md, .flow/usage.md, plus the plugin's flowctl docs reference + root README's what's-new callout. Maintainer-only (mickel.tech website) is skipped per convention.

**Size:** M
**Files:**
- `CHANGELOG.md` (new `[flow-next 0.39.0]` block)
- `CLAUDE.md` (root — commands list, memory system block, new Glossary section)
- `plugins/flow-next/README.md` (what's-new callout, commands table, memory tree, frontmatter schema, new Project Glossary section, audit/sync/scout extensions noted)
- `README.md` (root — what's-new callout)
- `.flow/usage.md` (new Glossary section)
- `plugins/flow-next/docs/flowctl.md` (memory category list, new glossary subcommand reference section)

## Approach

Per `docs-gap-scout` findings (gathered during planning), update in this order:

1. **CHANGELOG.md** — new `## [flow-next 0.39.0] - YYYY-MM-DD` block above 0.38.2. Sections:
   - `### Added`: GLOSSARY.md artifact + flowctl glossary subcommands; knowledge/decisions/ category + frontmatter fields; /flow-next:interview --docs/--no-docs autodetect; doc-aware behaviors (a/b/c/d).
   - `### Changed`: docs-gap-scout extends scan; /flow-next:audit walks glossary terms + decisions; /flow-next:sync detects glossary renames + decision overrides; R17 grep guard added.
   - `### Notes`: closed-epic foundations (fn-30 / fn-34 / fn-36 / fn-15-96t); explicitly call out R18 (uninstall survival) since it's a tenet-driven design choice.

2. **CLAUDE.md** (lines 19-27, 65-86, ~97):
   - Commands list: `/flow-next:interview` bullet gains `--docs` / `--no-docs` + autodetect description.
   - Memory system block: add `decisions` to knowledge category list; document optional decision-specific fields.
   - **New** Glossary section after Prospecting block: GLOSSARY.md placement, `flowctl glossary` subcommands, nearest-ancestor resolution rule, R18 (survives uninstall).

3. **plugins/flow-next/README.md** (lines 24, 56, 1499, 1508, 1549, 1618, 1687, 1691, 1814, 1979, 2093):
   - What's-new callout (line ~24): v0.39.0 one-liner.
   - Commands table interview row: doc-aware mode mentioned.
   - Memory system directory tree (line ~1525): add `decisions/`.
   - Frontmatter schema: add decision-specific optional fields.
   - **New** Project Glossary section after Memory System.
   - Audit lifecycle: extended (glossary + decisions walks).
   - Plan-sync: extended (glossary renames + decision overrides).
   - Planning Phase docs-gap-scout bullet: extended scan list.

4. **README.md (root)** — what's-new callout (lines 28-32) updated to v0.39.0 with one-line summary (glossary + decisions + doc-aware interview).

5. **.flow/usage.md** — new `# Glossary (v0.39.0+)` section after memory commands block (line ~86), one-liner per `flowctl glossary` subcommand.

6. **plugins/flow-next/docs/flowctl.md** — memory category list (line ~505) adds `decisions`; new `### glossary` section at end (after the `prospect` section ~line 591) documenting all four subcommands + `--definition-file` variant.

7. **R17 compliance**: no DDD jargon in any updated docs (manual review; T7 grep guard catches regressions).
8. **No website changes** — `~/work/mickel.tech/app/apps/flow-next/page.tsx` is maintainer-only per CLAUDE.md convention. Skip.

## Investigation targets

**Required:**
- `CLAUDE.md` lines 19-27, 65-86 (commands + memory blocks)
- `plugins/flow-next/README.md` lines 24, 56, 1499-1531, 1549-1561, 1618-1632, 1687-1691, 1814-1842, 1979-1984, 2093-2109
- `CHANGELOG.md` lines 1-50 (current 0.38.2 entry as shape template)
- `README.md` lines 28-32 (current what's-new callout)
- `.flow/usage.md` lines 76-86 (memory commands block)
- `plugins/flow-next/docs/flowctl.md` lines 505-590 (memory + prospect sections as templates)

## Acceptance

- [ ] CHANGELOG.md has `[flow-next 0.39.0]` block covering R1-R18 changes (Added / Changed / Notes structure)
- [ ] CLAUDE.md commands list, memory system block, and new Glossary section all updated
- [ ] plugins/flow-next/README.md: what's-new callout + commands table + memory tree + frontmatter schema + new Project Glossary section + audit/sync/scout extension notes
- [ ] Root README.md what's-new callout updated to v0.39.0
- [ ] .flow/usage.md gains Glossary section
- [ ] plugins/flow-next/docs/flowctl.md adds `decisions` to memory categories list + new glossary subcommand reference section
- [ ] No DDD terminology in any updated docs (R17 — manually verify; T7 grep guard catches future regressions)
- [ ] Maintainer-only website (mickel.tech) NOT updated in this task (per CLAUDE.md convention)
- [ ] Version bump considered: this epic adds skill behavior (interview), so a version bump (likely 0.39.0) is warranted per CLAUDE.md versioning rules. The bump itself is the release-handoff step, not part of this task's acceptance — but the CHANGELOG entry must use the agreed version.

## Done summary

## Evidence
