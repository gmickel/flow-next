# Memory System

Persistent learnings that survive context compaction. Opt-in, categorized — v0.33.0+. One entry per file, YAML frontmatter, two tracks (`bug` / `knowledge`).

## Directory tree

```
.flow/memory/
├── bug/
│   ├── build-errors/
│   ├── test-failures/
│   ├── runtime-errors/
│   ├── performance/
│   ├── security/
│   ├── integration/
│   ├── data/
│   └── ui/
└── knowledge/
    ├── architecture-patterns/
    ├── conventions/
    ├── tooling-decisions/
    ├── workflow/
    ├── best-practices/
    └── decisions/                          # v0.39.0+ — load-bearing architectural choices
```

## Frontmatter schema (bug track)

```yaml
---
title: SQLite locked under concurrent writes
date: 2026-04-24
track: bug
category: runtime-errors
module: storage/sqlite
tags: [sqlite, concurrency, locking]
problem_type: race
root_cause: missing WAL mode
resolution_type: config-fix
---
```

## Frontmatter schema (knowledge track)

```yaml
---
title: Prefer flowctl rp wrappers over the direct RepoPrompt CLI
date: 2026-04-24
track: knowledge
category: conventions
module: scripts/ralph
tags: [rp, ralph, review]
applies_when: writing Ralph loop scripts or review shims
---
```

## Frontmatter schema (decisions — knowledge track, v0.39.0+)

```yaml
---
title: Use nearest-ancestor walk for GLOSSARY.md resolution
date: 2026-04-30
track: knowledge
category: decisions
module: glossary
tags: [glossary, resolution, walk]
decision_status: accepted          # proposed | accepted | superseded
alternatives_considered: |
  - always-root: simpler, but loses subdir flexibility
  - explicit-path: makes resolution opaque to skills
superseded_by: null                 # set when decision_status = superseded
---
```

Decision body convention: 1–3 sentence floor describing trade-offs, irreversibility, and surprise factor. The three decision-specific fields (`decision_status`, `superseded_by`, `alternatives_considered`) are permitted on any knowledge entry but specifically intended for the `decisions/` subtree. Constants `MEMORY_DECISION_FIELDS` / `MEMORY_DECISION_STATUSES` (alongside `MEMORY_KNOWLEDGE_FIELDS` / `MEMORY_STATUS`).

## Enable + init

```bash
flowctl config set memory.enabled true
flowctl memory init   # creates directory tree
```

## Add

```bash
flowctl memory add \
  --track bug \
  --category runtime-errors \
  --title "SQLite locked under concurrent writes" \
  --module storage/sqlite \
  --tags "sqlite,concurrency" \
  --body-file /tmp/writeup.md

flowctl memory add \
  --track knowledge \
  --category conventions \
  --title "Prefer flowctl rp wrappers" \
  --module scripts/ralph \
  --tags "rp,ralph"
```

`--type pitfall|convention|decision` (the old API) still works but emits a deprecation warning. Removed in 0.36.0.

**Overlap scoring** runs on every `add` and the JSON response always emits `matches` (with scores) as a retrieval signal. `memory add` **always creates** a new entry unless the caller passes explicit `--update <id>` (fn-113 — flowctl never auto-mutates on high overlap). Moderate overlap may set `related_to: [existing-id]` on the new entry. Callers (skills) read `matches` and either re-run with `--update <id>` or accept the create.

## Query

```bash
flowctl memory list                                # default: active only
flowctl memory list --track bug                    # filter by track
flowctl memory list --category runtime-errors      # filter by category
flowctl memory list --status all                   # include stale entries

flowctl memory search "sqlite locked"              # default: --status active
flowctl memory search "sqlite locked" --status stale  # only stale entries
flowctl memory search "sqlite locked" --status all    # active + stale
flowctl memory search "rp wrappers" \
  --module scripts/ralph \
  --tags "rp,ralph" \
  --limit 5

flowctl memory read bug/runtime-errors/sqlite-locked-2026-04-24   # full id
flowctl memory read sqlite-locked-2026-04-24                       # slug+date
flowctl memory read sqlite-locked                                  # slug only (latest date)
flowctl memory read legacy/pitfalls.md                             # legacy flat file
flowctl memory read legacy/pitfalls#3                              # legacy entry (1-based)
```

Search scoring is weighted: title 5×, tags 3×, body 1.5×, misc 1×. Legacy hits surface as synthetic entries with `track: "legacy"`. Default `--status active` excludes stale entries (audit-flagged advice stops polluting `memory-scout` output); pass `--status stale` or `--status all` to include them.

## Audit lifecycle (v0.37.0+)

`/flow-next:audit [mode:autofix] [scope hint]` walks `.flow/memory/`, reviews each entry against the current codebase, and decides per entry whether to **Keep / Update / Consolidate / Replace / Delete**. Interactive mode (default) asks via the platform's blocking-question tool; autofix mode applies unambiguous actions and marks ambiguous entries as stale. The skill is agent-native — host agent reads the workflow markdown and executes it directly using its own Read/Grep/Glob tools (no Python audit engine, no codex/copilot subprocess dispatch). Legacy flat files are skipped with a warning.

**Audit extensions (v0.39.0+):** Phase 0.5 (new) reads every `GLOSSARY.md` on the ancestor chain and audits each term against the current code (any references intact? renamed? gone?). Phase 0.1 (extended) auto-walks `knowledge/decisions/` alongside other categories. **Replace outcomes for decision entries are supersede-not-delete** — the audit writes a new entry with `decision_status: accepted` and sets the old entry's `decision_status: superseded` + `superseded_by: <new-id>`, preserving the historical trail. Other categories keep the existing Replace semantics.

Two flowctl helpers back the audit lifecycle (also callable directly):

```bash
# Mark an entry stale (used by /flow-next:audit, also callable directly)
flowctl memory mark-stale <id> --reason "module renamed in PR #123"
flowctl memory mark-stale <id> --reason "..." --audited-by "/flow-next:audit"
flowctl memory mark-stale <id> --reason "..." --json

# Clear stale flag
flowctl memory mark-fresh <id>
```

`mark-stale` sets `status: stale`, stamps `last_audited` (UTC), records `audit_notes` from `--reason`. Body is never modified. Idempotent — re-marking replaces `audit_notes` and re-stamps the date. `mark-fresh` drops the stale fields and stamps `last_audited`.

## Migrate legacy → categorized (v0.37.0+)

`/flow-next:memory-migrate [mode:autofix] [scope hint]` is the recommended path. Agent-native skill — host agent reads each legacy entry, classifies it into the right `(track, category)` pair using its own intelligence + repo context, writes a categorized entry via `flowctl memory add`. Interactive mode (default) asks via the platform's blocking-question tool on ambiguous entries; autofix mode accepts mechanical defaults and logs ambiguous as `needs-review`. Optional scope hint narrows to a single legacy file (e.g. `/flow-next:memory-migrate pitfalls.md`). Phase 4 cleanup writes a self-ignoring `.flow/memory/_migrated/.gitignore` and renames originals on user consent (autofix declines by default; never auto-deletes).

```bash
flowctl memory list-legacy            # text mode: filename + entry count + mechanical default per entry
flowctl memory list-legacy --json     # {files: [{filename, entry_count, entries: [...]}]}
```

`memory list-legacy` is the parsing helper the skill consumes; also useful for ad-hoc inspection. Each entry carries `mechanical_track` / `mechanical_category` derived from the source filename so the agent has a sane default to override only when content warrants.

### Automation / CI fallback

```bash
flowctl memory migrate --dry-run      # print plan (mechanical-only)
flowctl memory migrate --yes          # apply (mechanical-only)
```

`flowctl memory migrate` is **deterministic-only** since v0.37.0 — uses the mechanical filename → `(track, category)` heuristic. The `--no-llm` flag is accepted-but-noop (kept for back-compat with scripted callers). For accurate per-entry classification, run the `/flow-next:memory-migrate` skill instead.

`migrate` is idempotent — re-running after legacy files are archived prints `No legacy files to migrate.` JSON mode refuses writes without `--yes` as a safety guard.

> **Removed in v0.37.0:** `FLOW_MEMORY_CLASSIFIER_BACKEND`, `FLOW_MEMORY_CLASSIFIER_MODEL`, `FLOW_MEMORY_CLASSIFIER_EFFORT` env vars are no longer consumed (subprocess classifier dispatch removed). Setting them now triggers a one-time stderr warning. Suppress via `FLOW_NO_DEPRECATION=1`.

## Surface the store in AGENTS.md / CLAUDE.md

Point agents at `.flow/memory/` with a one-line note in `AGENTS.md` / `CLAUDE.md` (or both). `/flow-next:audit` and setup already handle discoverability via Edit; there is no dedicated `flowctl memory` patch command.

## When enabled

- **Planning**: category-aware `memory-scout` runs in parallel with other scouts, returns track/category-tagged hits and prioritizes module matches.
- **Work**: worker reads relevant entries during re-anchor.
- **Ralph**: worker writes structured bug-track entries via `memory add --track bug --category <c>` on NEEDS_WORK → SHIP. Overlap scoring emits `matches`; the worker re-runs with `--update <id>` when folding into a known prior entry.

Config lives in `.flow/config.json`, separate from Ralph's `scripts/ralph/config.env`.

## Upgrading from 0.32.x

1. `git pull && (reinstall plugin)`.
2. **Recommended:** run `/flow-next:memory-migrate` for agent-native per-entry classification (host agent reads each legacy entry and picks the right `(track, category)` with full repo context). Or `/flow-next:memory-migrate mode:autofix` to accept mechanical defaults without prompts.
3. **Automation alternative:** `flowctl memory migrate --dry-run` then `flowctl memory migrate --yes` for deterministic mechanical-only classification (legacy files move to `.flow/memory/_legacy/`; migration is idempotent).
4. Optional: add a one-line `.flow/memory/` pointer in `AGENTS.md` / `CLAUDE.md` so agents without flow-next skills still find the store.

Until migration runs, legacy flat files continue to work; `list` / `read` / `search` read both.

## See also

- [`architecture.md`](architecture.md) — `.flow/` directory layout including the `memory/` tree.
- [`glossary.md`](glossary.md) — pairs naturally with the `knowledge/decisions/` subtree (terminology + load-bearing choices).
- [`strategy.md`](strategy.md) — `/flow-next:capture` source-tags strategy-derived AC as `[strategy:<track>]`; decisions are recorded via memory when capture refuses to write against an active track.
- [`flowctl.md`](flowctl.md) — full `flowctl memory` reference (every subcommand, flag, JSON shape).
