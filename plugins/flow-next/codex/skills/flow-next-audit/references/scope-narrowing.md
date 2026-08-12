# Scope narrowing (gated reference)

> **Loaded only when a Phase 0 branch points here** — a non-empty `SCOPE_HINT`
> (§0.3), or `TOTAL >= 9` after filtering (§0.5). A full sweep of a small store
> takes neither branch and never reads this file.

Contents:

- [0.3 — Apply scope hint (when present)](#03--apply-scope-hint-when-present) — the five-step first-match-wins narrowing order
- [0.5 — Broad-scope triage (only when `TOTAL >= 9`)](#05--broad-scope-triage-only-when-total--9) — cluster scoring and the interactive / autofix routes

### 0.3 — Apply scope hint (when present)

When `SCOPE_HINT` is non-empty, narrow the candidate set in this order — first match wins:

1. **Track match** — `bug` or `knowledge` as a literal token. Filter to that track.
2. **Category match** — exact match against `MEMORY_CATEGORIES` enum (e.g. `runtime-errors`, `architecture-patterns`, `tooling-decisions`). Filter to that category across both tracks.
3. **Module match** — substring match against `frontmatter.module`. Useful when the user types `auth` or `plugins/flow-next/scripts/flowctl.py`.
4. **Tag match** — exact match against any value in `frontmatter.tags`.
5. **Title / body keyword** — case-insensitive substring search across `title` and `body`. Last resort because it can be noisy.

Print the strategy used and the count: `Scope hint "auth" matched module field on 4 entries.`

If no entries match, **interactive**: ask whether to (a) widen to all entries, (b) re-enter a different hint, (c) abort. **Autofix**: print `Scope hint "<hint>" matched zero entries — nothing to audit.` and exit cleanly.
---

### 0.5 — Broad-scope triage (only when `TOTAL >= 9`)

Group entries by `(module, category)` pair. For each cluster:

- Count entries.
- Note cross-references (`related_to` frontmatter field pointing into the same cluster).
- Spot-check drift: does the most-referenced file in the cluster still exist? Use Glob.

Compute impact: `cluster_score = entries + 2 * cross_refs + (3 if missing_anchor_file else 0)`. The highest-scoring cluster is the recommended starting area.

**Interactive:** present top cluster + 2 alternatives via plain-text numbered prompt:

```
Found 24 entries across 6 clusters.

The auth/runtime-errors cluster has 5 entries cross-referencing each other —
3 reference files that no longer exist on disk. Highest staleness signal.

Options:
  1. Start with auth/runtime-errors (recommended)
  2. Pick a different cluster
  3. Audit everything (will take longer)
```

**Autofix:** process all clusters in impact order (highest first). Print the queue order so the report shows what got prioritized.
