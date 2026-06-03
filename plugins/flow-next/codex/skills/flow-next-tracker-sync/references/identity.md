# Hybrid identity / naming model (R16)

How a synced spec is keyed. The two id schemes **coexist**; resolution is provided by fn-52.10's widened resolver (`is_spec_id` / `expand_bare_spec_id`), so the scaffold just calls flowctl and relies on it. **Ids NEVER change — there is no rename-on-push.**

## The two origins

### Tracker-first — natively keyed by the tracker key

A spec pulled from a tracker issue ("grab issue X and spec it") IS keyed by the tracker key, so the repo artifact mirrors the board (matching the manual workunits convention `wor-2-…`):

| | value |
|---|---|
| canonical spec id | `wor-17-slug` |
| canonical task ids | `wor-17-slug.M` (the existing `task_id = <spec-id>.N` rule) |
| branch | `wor-17-slug` |
| bare aliases | `wor-17` / `wor-17.M` — resolve exactly as `fn-52` / `fn-52.M` expand to the full-slug id today |

Create it with:

```bash
$FLOWCTL spec create --tracker-first --tracker-identifier "WOR-17" --title "<issue title>" --json
```

`--tracker-first` keys the spec by the tracker identifier instead of allocating a fresh `fn-NN`. No second id; no rename.

### Flow-first — keep `fn-NN`, gain a resolvable alias

A spec authored in flow (capture/interview/plan) keeps its sequential `fn-NN-slug` handle (project convention preserved). On push, the tracker key is stored in the single `tracker.identifier` field (R4) as a **resolvable alias**:

```bash
$FLOWCTL sync set-tracker-id "fn-42-foo" "$ISSUE_UUID" --identifier "WOR-99" --url "$ISSUE_URL"
```

Now `work wor-99`, `show wor-99`, etc. resolve to `fn-42-foo` **without renaming it**. The issue carries the flow id back via a `flow:fn-42-foo` label and/or a `[fn-42-foo]` title prefix.

## Resolution (fn-52.10 — the scaffold does NOT reimplement this)

- The tracker key is a **first-class, resolvable handle**, not just a stored label: `work wor-17`, `plan wor-17`, `show wor-17`, tasks `wor-17.M` all resolve. flowctl widened `is_spec_id` / `expand_bare_spec_id` so every command inherits resolution.
- **Case:** `tracker.identifier` stores the display form (`WOR-17`); the canonical id derives from the lowercase key (`wor-17-slug`); alias resolution is case-insensitive.
- The native `fn-` prefix is reserved for the sequential scheme; tracker-key resolution is tried only after the `fn-` path misses. Enumeration sees tracker-key specs, but native `fn-N` allocation counts `fn-*` only — a `wor-9999` never bumps the next `fn`.
- **One tracker team / workspace per repo** — the bridge assumes a single team key so a bare `wor-17` resolves unambiguously. Cross-workspace same-key collision (two teams both keyed `WOR`) is out of scope and not disambiguated.

> The id-grammar widening had to cover the FULL command surface, not just the named lifecycle commands (memory: `id-grammar-widening-must-cover-the-full`). That work is fn-52.10's; the scaffold relies on it being complete and only calls `flowctl <cmd> wor-17`.

## Hard rules — never violate

- **No rename-on-push.** Existing spec/task ids, branches, and dep edges are never mutated when a spec is synced; the tracker key is added as a resolvable handle/alias, not a replacement.
- **`spec set-title` on a tracker-linked spec updates the title only** — it does NOT re-slug / rename the canonical id, branch, or files (that would desync the linkage). Unlinked specs keep today's rename behavior.
- **Surface `identifier` in sync listings** so users see both handles (the canonical flow id and the board-facing `WOR-17`).
- This is **additive** — it does NOT require the separate `fn-NN`-deprecation id-scheme change to land first; that change, when it comes, only governs *removing* `fn-NN`, not *also accepting* the tracker key.
