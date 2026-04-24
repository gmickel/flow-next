# fn-30-memory-schema-upgrade.4 flowctl memory migrate + fast-model classifier

## Description

New command: `flowctl memory migrate`. Converts legacy flat files (`pitfalls.md`, `conventions.md`, `decisions.md`) into categorized YAML-frontmatter entries via fast-model classification. Dry-run + confirmation flags for safety.

**Size:** M

**Files:**
- `plugins/flow-next/scripts/flowctl.py` — `cmd_memory_migrate`, classifier helper
- `.flow/bin/flowctl.py` (mirror)
- Unit tests (with stub LLM invocation)

## CLI signature

```
flowctl memory migrate [--dry-run] [--yes] [--no-llm] [--json]
```

- `--dry-run`: print plan without writing any files
- `--yes`: skip interactive confirmation (still respects `--dry-run`)
- `--no-llm`: skip LLM classification; use mechanical mapping only (pitfall→bug/build-errors, convention→knowledge/conventions, decision→knowledge/tooling-decisions)
- `--json`: machine-readable output

## Behavior

1. **Detect legacy files** in `.flow/memory/`:
   - `pitfalls.md`
   - `conventions.md`
   - `decisions.md`

   If none found, print "No legacy files to migrate." and exit 0.

2. **Parse entries** from each legacy file. The current flat format uses `---` as entry delimiter. Each entry has:
   - First line: title (heading or bullet)
   - Following lines: body prose
   - Tags: extract from inline tags like `#perf` if present

3. **Classify** each entry:
   - Mechanical default: `pitfalls.md` → `bug` track; `conventions.md` → `knowledge/conventions`; `decisions.md` → `knowledge/tooling-decisions`
   - If `--no-llm` or classifier unavailable: use defaults
   - Otherwise: invoke fast model (haiku / gpt-5.4-mini) with prompt:

     ```
     Classify this memory entry into track + category.

     Tracks: bug | knowledge
     Bug categories: build-errors, test-failures, runtime-errors, performance, security, integration, data, ui
     Knowledge categories: architecture-patterns, conventions, tooling-decisions, workflow, best-practices

     Entry source file: {pitfalls|conventions|decisions}.md
     Entry title: <title>
     Entry body: <body>

     Output exactly one line: track/category
     Example: bug/runtime-errors
     ```

4. **Construct frontmatter** for each classified entry:
   - `title`: from source
   - `date`: from source (if dated) or today
   - `track`, `category`: from classification
   - `tags`: from extracted inline tags + category slug
   - `problem_type` (bug track): infer from category (category matches problem-type enum 1:1)
   - `symptoms`, `root_cause`: heuristic parse from body structure; leave blank if unclear
   - `resolution_type` (bug track): default `fix`
   - `applies_when` (knowledge track): first sentence of body

5. **Print plan**:

   ```
   Migration plan:

   From pitfalls.md (3 entries):
     → bug/runtime-errors/null-deref-auth-2026-03-15.md
     → bug/build-errors/missing-dep-import-2026-03-18.md
     → bug/performance/n-plus-one-query-2026-04-02.md

   From conventions.md (1 entry):
     → knowledge/conventions/prefer-satisfies-over-as-2026-04-10.md

   From decisions.md (2 entries):
     → knowledge/tooling-decisions/use-biome-for-formatting-2026-02-14.md
     → knowledge/tooling-decisions/adopt-bun-over-npm-2026-03-01.md

   Legacy files will be moved to .flow/memory/_legacy/ (preserved).

   Proceed? [y/N]
   ```

6. **On confirmation** (or `--yes`):
   - Write each new entry file
   - Move legacy files to `.flow/memory/_legacy/<name>.md`
   - Create `.flow/memory/README.md` if absent
   - Print summary: `Migrated 6 entries; legacy files preserved at .flow/memory/_legacy/`

7. **On `--dry-run`**: print plan and exit without writing.

## Rollback

The migrate command is idempotent only for legacy files. If a user runs it twice and the legacy files are already moved, it prints "No legacy files to migrate." No rollback command is provided — `git` handles undo.

## Fallback if LLM unavailable

If the fast model call fails (network, auth, backend not configured), fall back to mechanical mapping + print warning:

> LLM classifier unavailable ({reason}). Using mechanical defaults. Re-run with `--no-llm` to suppress this warning.

## JSON output (--json)

```json
{
  "success": true,
  "migrated": [
    {"source": "pitfalls.md", "source_entry": 1, "target": "bug/runtime-errors/null-deref-auth-2026-03-15", "method": "llm"},
    ...
  ],
  "legacy_moved_to": ".flow/memory/_legacy/",
  "warnings": []
}
```

## Acceptance

- **AC1:** `migrate --dry-run` prints plan without writing.
- **AC2:** `migrate --yes` skips confirmation and migrates atomically.
- **AC3:** Without `--yes`, user prompt appears; declining aborts without changes.
- **AC4:** Classified entries land in correct `<track>/<category>/` directory with valid frontmatter.
- **AC5:** Legacy files moved to `.flow/memory/_legacy/` after migration.
- **AC6:** `--no-llm` uses mechanical defaults (bug/build-errors for pitfalls, knowledge/conventions for conventions, knowledge/tooling-decisions for decisions).
- **AC7:** LLM unavailable falls back to mechanical mapping with warning.
- **AC8:** Running migrate twice (after first success) is a no-op with informative message.
- **AC9:** Unit tests: feed synthetic legacy files, stub LLM responses, verify output structure.

## Dependencies

- fn-30-memory-schema-upgrade.1 (schema)
- fn-30-memory-schema-upgrade.2 (memory add — used internally by migrate to write entries, or direct file writes if simpler)

## Notes from fn-30.2 (plan-sync)

Helpers landed in `flowctl.py` that this task can reuse instead of rolling its own file-writer:

- `write_memory_entry(path, frontmatter, body)` — validates frontmatter, enforces deterministic field order, quotes YAML scalars that would otherwise coerce (dates/bools/numbers).
- `_memory_entry_id(track, category, slug, date)` / `_memory_entry_path(memory_dir, track, category, slug, date)` — canonical id / path builders.
- `_memory_resolve_legacy_type(name)` — mechanical fallback maps `pitfall[s]` → `bug/build-errors`, `convention[s]` → `knowledge/conventions`, `decision[s]` → `knowledge/tooling-decisions`.
- `MEMORY_CATEGORIES`, `MEMORY_PROBLEM_TYPES`, `MEMORY_RESOLUTION_TYPES` constants are the authoritative enums.

`memory add` JSON output shape (for call-through paths): `{success, entry_id, path, overlap_level, related_to, action: "created"|"updated", warnings}`. Same-day slug collisions are auto-disambiguated with a `-2`, `-3`, ... suffix in the slug. `--no-overlap-check` is the right flag when migrate wants to force a clean import without dedup against in-progress writes.

<!-- Updated by plan-sync: fn-30.2 exposes write_memory_entry / _memory_entry_id / _memory_resolve_legacy_type helpers migrate can reuse. -->


## Done summary
memory migrate + fast-model classifier shipped.

- `flowctl memory migrate` converts legacy flat files to categorized entries.
- Entries split on `\n---\n` separators per legacy-file convention.
- Fast-model classifier (codex/copilot, auto-detected via FLOW_MEMORY_CLASSIFIER_BACKEND, gpt-5.4-mini/claude-haiku-4.5 defaults) routes each entry to a specific category; failures fall back to mechanical map.
- Mechanical map: pitfalls→bug/build-errors, conventions→knowledge/conventions, decisions→knowledge/tooling-decisions.
- `--dry-run` prints plan, `--yes` skips confirmation, `--no-llm` forces mechanical.
- Legacy files archived to `.flow/memory/_legacy/` after migrate.
- Idempotent.

Smoke: 95/95 pass (was 94).
## Evidence
- Commits: 6950f64
- Tests: plugins/flow-next/scripts/smoke_test.sh memory migrate block (dry-run, real, idempotency)
- PRs: