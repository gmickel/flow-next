# Memory schema upgrade: categorized YAML-frontmatter learnings with overlap detection and Ralph auto-capture rewrite

## Overview

Upgrade flow-next's opt-in memory system from 3 flat markdown files (`pitfalls.md`, `conventions.md`, `decisions.md`) to a categorized tree of YAML-frontmatter-bearing entries. Bug track + knowledge track. Overlap detection on add. Ralph auto-capture writes structured entries instead of appending prose.

Inspired by MergeFoundry upstream's compounding-learnings pattern — richer schema, category-scoped retrieval, explicit overlap handling, and discoverability plumbing in project instruction files.

The upgrade is strictly additive for users who've already initialized memory; a `flowctl memory migrate` converts old flat files in place.

## Constraints (CRITICAL)

- Backward compatibility: existing `.flow/memory/pitfalls.md` / `conventions.md` / `decisions.md` must continue to work until the user runs migration
- `flowctl memory search` / `flowctl memory list` / `flowctl memory read` all work across old + new format during transition
- Ralph's current NEEDS_WORK auto-capture continues to produce useful entries during transition; the rewrite lands atomically with the migration tool
- No new external dependencies (pure Python + stdlib YAML via `PyYAML` — check if already vendored; if not, use a minimal inline parser or require users to install it once)
- Opt-in remains the default — memory is NOT initialized automatically on `flowctl init`
- Cross-platform (Claude Code, Codex, Copilot, Droid) — memory files live under `.flow/memory/` regardless of platform

## Design & Data Models

### Directory tree

Before:

```
.flow/memory/
  pitfalls.md
  conventions.md
  decisions.md
```

After (all paths under `.flow/memory/`):

```
bug/
  build-errors/
  test-failures/
  runtime-errors/
  performance/
  security/
  integration/
  data/
  ui/
knowledge/
  architecture-patterns/
  conventions/
  tooling-decisions/
  workflow/
  best-practices/
```

Each category directory contains entries. Filename convention: `<slug>-YYYY-MM-DD.md`.

### Entry schema (YAML frontmatter)

Common fields (all tracks):

```yaml
---
title: <one-line summary, max 80 chars>
date: YYYY-MM-DD
track: bug | knowledge
category: <one of the category enum values>
module: <optional — affected module/file/subsystem>
tags: [tag1, tag2, ...]
---
```

Bug-track additional fields:

```yaml
problem_type: build-error | test-failure | runtime-error | performance | security | integration | data | ui
symptoms: <one-line>
root_cause: <one-line>
resolution_type: fix | workaround | documentation | refactor
```

Knowledge-track additional fields:

```yaml
applies_when: <one-line — situations this guidance applies to>
```

Optional fields (both tracks):

```yaml
status: active | stale   # ce-compound-refresh maintenance marker
stale_reason: <reason>    # only when status: stale
stale_date: YYYY-MM-DD    # only when status: stale
last_updated: YYYY-MM-DD
related_to: [entry-id-1, entry-id-2]   # entries this one overlaps with or supersedes
```

Body structure (both tracks): short prose with sections. Bug track: Problem / What Didn't Work / Solution / Prevention. Knowledge track: Context / Guidance / When to Apply / Examples.

### Overlap detection

On `flowctl memory add`, compute a fingerprint and scan existing entries for matches:

- **Fingerprint:** normalized title + sorted tags + module
- **Thresholds:**
  - High overlap (≥3 of 4 dimensions match): title substring AND any tag AND module match → **update existing in place**, add `last_updated: YYYY-MM-DD`
  - Moderate overlap (2 of 4 dimensions): → **create new** but set `related_to: [existing-entry-id]`; print a warning with the related entries
  - Low overlap: create new, no related_to

Implementation is a simple Python loop over entries in the target category directory — no vector search. Sufficient for the expected memory size (tens to low hundreds of entries per project).

### Ralph auto-capture rewrite

Current behavior (pre-fn-30): on NEEDS_WORK verdict, Ralph appends prose to `.flow/memory/pitfalls.md`.

New behavior: Ralph writes a structured bug-track entry. Flow:

1. Ralph's worker captures:
   - Review verdict (NEEDS_WORK or MAJOR_RETHINK)
   - Primary issue categories from the review prose (build-error / test-failure / etc.)
   - Affected files (for `module`)
   - Resolution applied
2. Worker calls:

   ```bash
   flowctl memory add \
     --track bug \
     --category <inferred-category> \
     --title "<summary>" \
     --module "<affected-module>" \
     --tags "<tag1>,<tag2>" \
     --problem-type <type> \
     --body-file /tmp/memory-body.md
   ```

3. `flowctl memory add` runs overlap detection; either updates existing or creates new.

The worker agent prompt (`worker.md`) gets a new section describing this capture flow and when to invoke it (only after a successful fix, not on every cycle).

### Migration tool

New command: `flowctl memory migrate [--dry-run] [--yes]`.

Behavior:
1. Detect legacy files: `.flow/memory/pitfalls.md`, `conventions.md`, `decisions.md`.
2. Parse each — split on `---` separators (current flat format uses them as entry delimiters).
3. For each entry, classify track + category via LLM judgment (fast model — haiku / gpt-5.4-mini):
   - pitfalls.md → bug track, category inferred from entry content
   - conventions.md → knowledge/conventions
   - decisions.md → knowledge/tooling-decisions
4. For each classified entry, construct YAML frontmatter + body, write to `.flow/memory/<track>/<category>/<slug>-<date>.md`.
5. Rename legacy files to `.flow/memory/_legacy/<name>.md` (preserved for reference; not read by skills).
6. Update `.flow/memory/README.md` (generated) describing the new structure.

Flags:
- `--dry-run` prints the plan without writing
- `--yes` skips the confirmation prompt
- No flag → prompts user to confirm before writing (interactive safety)

### flowctl memory command changes

All subcommands gain category awareness:

```
flowctl memory init                             # creates tree structure, writes template README
flowctl memory add --track <bug|knowledge> --category <cat> --title <...> [--module <mod>] [--tags "a,b"] [--body-file <path>] [--json]
flowctl memory list [--track <bug|knowledge>] [--category <cat>] [--json]
flowctl memory read <entry-id> [--json]
flowctl memory search <query> [--track <bug|knowledge>] [--category <cat>] [--json]
flowctl memory migrate [--dry-run] [--yes]
flowctl memory refresh [--dry-run]              # future: ce-compound-refresh-style maintenance (separate follow-up)
```

Entry ID format: `<track>/<category>/<slug>-<date>` (matches filepath).

Backward compatibility for `--type`: if `--type pitfall|convention|decision` is passed instead of `--track/--category`, auto-map:
- `pitfall` → `--track bug --category build-errors` (with warning to use new flags)
- `convention` → `--track knowledge --category conventions`
- `decision` → `--track knowledge --category tooling-decisions`

### Discoverability patch (AGENTS.md)

New command: `flowctl memory discoverability-patch [--apply] [--dry-run]`.

Scans the project's root AGENTS.md / CLAUDE.md for any mention of `.flow/memory/`. If absent, proposes a one-line addition in the appropriate section:

```
.flow/memory/   # categorized learnings store — searchable via `flowctl memory search`
```

Opt-in, interactive confirmation. This ensures agents that don't load flow-next skills still discover the memory store.

## File change map

### flowctl.py (significant)
- `plugins/flow-next/scripts/flowctl.py` — refactor `cmd_memory_*` functions; add category tree creation; add overlap detection; add migration; add discoverability patch; extend `--track` / `--category` args
- `.flow/bin/flowctl.py` (mirror)

### Templates
- `plugins/flow-next/templates/memory/README.md.tpl` — describes new structure (written on `memory init`)
- `plugins/flow-next/templates/memory/bug-track-entry.md.tpl` — bug entry template
- `plugins/flow-next/templates/memory/knowledge-track-entry.md.tpl` — knowledge entry template

### Agents
- `plugins/flow-next/agents/worker.md` — update NEEDS_WORK auto-capture section to use new command form
- `plugins/flow-next/agents/memory-scout.md` — teach scout to read categorized tree; return category-aware results

### Ralph harness (user-repo side, template)
- `plugins/flow-next/skills/flow-next-ralph-init/templates/scripts/ralph/ralph.sh` (or wherever auto-capture lives) — update capture command shape
- Verify via ralph_smoke_test.sh

### Docs
- `CHANGELOG.md`
- `plugins/flow-next/README.md` — memory section rewrite
- `CLAUDE.md` — memory conventions section
- `/Users/gordon/work/mickel.tech/app/apps/flow-next/page.tsx` — update memory description

### Codex mirror + bump
- `scripts/sync-codex.sh` run after prompt edits
- `scripts/bump.sh minor flow-next` (this is a minor bump — schema change)

## Ralph compatibility audit

| Concern | Handling |
|---------|----------|
| Existing users with `.flow/memory/pitfalls.md` | `flowctl memory migrate` converts in place; no runtime break |
| Ralph's auto-capture during transition | Old path continues to work (backward-compat in `memory add --type`); new path preferred once migration runs |
| memory-scout behavior | Reads both legacy and new formats transparently |
| Ralph template users who never migrate | Legacy flat files remain readable; no features gated on migration |

Ralph's receipt contract is unchanged. Memory is a separate surface.

## Acceptance criteria

- **R1:** `.flow/memory/` directory layout supports categorized tree under `bug/` and `knowledge/`.
- **R2:** YAML frontmatter schema is enforced on add: required fields validated, track-specific fields populated, unknown fields rejected with clear error.
- **R3:** `flowctl memory add` runs overlap detection; high overlap updates existing entry; moderate creates with `related_to` reference.
- **R4:** `flowctl memory list --track <t> --category <c>` returns filtered list.
- **R5:** `flowctl memory search <query>` searches entry body + frontmatter across all categories by default; flags narrow scope.
- **R6:** `flowctl memory migrate` converts legacy flat files into categorized entries via fast-model classification; `--dry-run` prints plan without writing; `--yes` skips confirmation.
- **R7:** Ralph worker auto-capture uses new `flowctl memory add --track bug --category <c>` form on NEEDS_WORK resolution.
- **R8:** memory-scout returns category-aware results with track + category columns.
- **R9:** Backward compatibility: `flowctl memory add --type pitfall|convention|decision` still works (auto-maps to new flags) with deprecation warning.
- **R10:** `flowctl memory discoverability-patch --apply` adds a one-line reference to `.flow/memory/` in the project's AGENTS.md or CLAUDE.md if absent; interactive by default.
- **R11:** Ralph smoke test (`ralph_smoke_test.sh`) passes with new memory schema.
- **R12:** Existing `.flow/memory/*.md` flat-file entries remain readable by `memory search` / `memory read` until migration runs.
- **R13:** Docs updated: plugin README memory section, CLAUDE.md memory bullets, website page, CHANGELOG entry.
- **R14:** `scripts/sync-codex.sh` regenerates Codex mirror cleanly.
- **R15:** Version bumped (minor: 0.33.0 → 0.34.0 or similar, chained after Epic 1).

## Boundaries

- Not adding vector search (BM25-grep is sufficient for expected corpus size).
- Not adding ce-compound-refresh drift maintenance in this epic (deferred to follow-up).
- Not changing the 3-type `--type` API entirely — backward compat is part of the contract.
- Not auto-running `discoverability-patch` on `memory init` — it's a separate opt-in command.
- Not introducing a centralized memory registry across projects (memory stays per-project).

## Risks

| Risk | Mitigation |
|------|------------|
| PyYAML not available on user systems | Use a minimal inline YAML parser for frontmatter only; PyYAML optional for round-trip write — if absent, write hand-formatted YAML (deterministic field order) |
| LLM classification during migration mis-categorizes entries | `--dry-run` shows plan; user confirms; misclassified entries can be moved with `mv` and fixed frontmatter |
| Overlap detection false positives (update when should have created new) | Only "high" threshold triggers update; user can override by passing explicit filename |
| Ralph auto-capture on every NEEDS_WORK cycle bloats memory | Worker prompt already says "only after successful fix"; add rule: don't capture if same fingerprint seen in last 24h |
| Breaking change for Ralph users during rollout | Backward-compat `--type` maps to new flags; legacy flat files continue to read |

## Decision context

**Why split bug/knowledge tracks:** MergeFoundry upstream data shows 80%+ of useful entries fall cleanly on one side. The split lets memory-scout filter efficiently and lets Ralph auto-capture only the bug track (knowledge is human-curated).

**Why category enum (not free-form tags):** enum catches typos (`preformance` vs `performance`), enables category-scoped list/search, forces classification discipline. Tags are additional free-form.

**Why overlap detection:** the #1 memory-store failure mode is accumulated duplicates that silently drift. Catching overlap at add-time prevents drift by construction.

**Why in-place migration (not greenfield):** Ralph harnesses in the wild already have `pitfalls.md` growing. Forcing users to start over wastes accumulated knowledge.

## Testing strategy

- Unit tests for frontmatter parse/write (round-trip)
- Unit tests for overlap detection with synthetic entry sets
- Unit tests for migration classifier fallback (when LLM unavailable, default to `knowledge/best-practices`)
- Integration smoke: `memory init` → `memory add` (high/moderate/low overlap) → `memory list` → `memory search`
- Ralph smoke: run `ralph_smoke_test.sh` with fresh `.flow/memory/`; verify auto-capture produces valid bug-track entry
- Migration smoke: seed a fake `pitfalls.md` with 5 entries, run `migrate --dry-run`, verify plan; run `migrate --yes`, verify output files

## Follow-ups (not in this epic)

- `flowctl memory refresh` — MergeFoundry-upstream-style ce-compound-refresh: Keep/Update/Consolidate/Replace/Delete classification against current code; autofix mode marks stale entries
- Cross-project memory sharing (if demand surfaces)
- TUI memory browser (if flow-next-tui matures)
