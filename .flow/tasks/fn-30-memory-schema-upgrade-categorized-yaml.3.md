# fn-30-memory-schema-upgrade.3 flowctl memory list + read + search with track/category filters

## Description

Rewrite `memory list`, `memory read`, `memory search` for the categorized tree. Preserve backward compatibility — reading flat legacy files continues to work.

**Size:** M

**Files:**
- `plugins/flow-next/scripts/flowctl.py` — `cmd_memory_list`, `cmd_memory_read`, `cmd_memory_search`
- `.flow/bin/flowctl.py` (mirror)
- Unit tests

## `memory list`

Signature:

```
flowctl memory list [--track <bug|knowledge>] [--category <cat>] [--status active|stale|all] [--json]
```

Behavior:
1. Walk `.flow/memory/` tree for entries (glob `*.md` under `<track>/<category>/`)
2. Also read legacy flat files if present (return as synthetic entries with `track: legacy`, `category: <derived-from-filename>`)
3. Filter by `--track`, `--category`, `--status`
4. Default `--status active` (don't show stale unless asked)

Output (human):

```
bug/runtime-errors/
  null-deref-in-auth-2026-05-01 — "Null deref in auth middleware" (module: src/auth.ts)
  timeout-in-webhook-2026-04-20 — "Webhook handler times out on large payloads" (module: src/webhooks.ts)

knowledge/conventions/
  prefer-satisfies-2026-05-02 — "Prefer `satisfies` over `as` for type assertions"

legacy/
  pitfalls.md (3 entries — run `flowctl memory migrate`)
  conventions.md (1 entry)
```

JSON output: flat array of `{entry_id, title, track, category, module, tags, date, status, path}`.

## `memory read`

Signature:

```
flowctl memory read <entry-id> [--json]
```

Entry ID matches one of:
- `bug/runtime-errors/null-deref-in-auth-2026-05-01` (full)
- `null-deref-in-auth-2026-05-01` (slug+date, unique lookup)
- `null-deref-in-auth` (slug — latest date wins)

Output: full markdown content + frontmatter (as-is on stdout).

JSON output:

```json
{
  "success": true,
  "entry_id": "...",
  "frontmatter": {...},
  "body": "..."
}
```

Legacy flat-file entries readable by passing the path: `memory read legacy/pitfalls.md` → prints entire file. Or `memory read legacy/pitfalls#3` to read the 3rd `---`-separated entry.

## `memory search`

Signature:

```
flowctl memory search <query> [--track <bug|knowledge>] [--category <cat>] [--module <mod>] [--tags "t1,t2"] [--limit <N>] [--json]
```

Behavior:
1. Walk memory tree (respecting filters)
2. Search query across: title (high weight), tags (medium), body (medium), frontmatter fields (low)
3. Simple BM25-like scoring or just token-overlap; don't overengineer — expected corpus is tens to low hundreds of entries
4. Also search legacy flat files (substring match in body)
5. Return ranked results with snippets

Output (human):

```
[bug/runtime-errors] null-deref-in-auth-2026-05-01 (score: 8.2)
  "Null deref in auth middleware"
  module: src/auth.ts
  > ...accessing user.role without guard leads to undefined which ...

[knowledge/conventions] prefer-satisfies-2026-05-02 (score: 3.1)
  "Prefer satisfies over as for type assertions"
  > ...using `satisfies` preserves the literal type while ensuring ...

[legacy/pitfalls.md] entry #2 (score: 2.4)
  > ...null check on req.user was missing...
```

JSON output: array of `{entry_id, title, track, category, score, snippet, path}`.

## Acceptance

- **AC1:** `memory list` walks the tree and prints grouped-by-category listing.
- **AC2:** `--track bug` filters to bug track only.
- **AC3:** `--category runtime-errors` filters to that category only.
- **AC4:** `--status stale` returns only stale entries (via frontmatter `status: stale`).
- **AC5:** `memory read` accepts full entry-id, slug+date, or just slug.
- **AC6:** `memory search "null deref"` returns relevance-ranked results across both tracks.
- **AC7:** Search covers legacy flat files in results (synthetic entry representation).
- **AC8:** `--json` outputs match documented schemas.
- **AC9:** Unit tests cover: list filtering, read by three ID forms, search ranking, legacy file coverage.

## Dependencies

- fn-30-memory-schema-upgrade.1 (schema + frontmatter helpers)

## Notes from fn-30.2 (plan-sync)

Helpers already in `flowctl.py` that list/read/search can reuse:

- `parse_memory_frontmatter(path)` — round-trip-safe YAML frontmatter reader (PyYAML when available, inline fallback otherwise).
- `_memory_parse_entry_filename(path)` — splits `<slug>-YYYY-MM-DD.md` into `(slug, date)`; returns `("", "")` when the stem doesn't match.
- `_memory_entry_id(track, category, slug, date)` — canonical id form `<track>/<category>/<slug>-<date>` (matches the filesystem path).
- `MEMORY_TRACKS`, `MEMORY_CATEGORIES`, `MEMORY_LEGACY_FILES` constants are the source of truth; use them instead of hard-coding category lists in the list/search walkers.

The current `cmd_memory_read` / `cmd_memory_list` / `cmd_memory_search` in flowctl.py still operate on legacy flat files only — this task is the rewrite. Preserve their current behavior for files whose names match `MEMORY_LEGACY_FILES` so backward compat holds until migration runs.

<!-- Updated by plan-sync: fn-30.2 added parse_memory_frontmatter / _memory_parse_entry_filename / _memory_entry_id helpers; list/read/search should reuse them. -->


## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
