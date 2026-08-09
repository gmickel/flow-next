# Hybrid identity / naming model (R16)

How a synced spec is keyed. The two id schemes **coexist**; resolution is provided by fn-52.10's widened resolver (`is_spec_id` / `expand_bare_spec_id`), so the scaffold just calls flowctl and relies on it. **Ids NEVER change — there is no rename-on-push.**

## The two origins

### Tracker-first — natively keyed by the tracker key

A spec pulled from a tracker issue ("grab issue X and spec it") IS keyed by the tracker key, so the repo artifact mirrors the board (matching the manual workunits convention `wor-2-…`):

| | value |
|---|---|
| canonical spec id | `wor-17-slug` / `gh-123-slug` / `gl-456-slug` |
| canonical task ids | `<canonical>.M` (the existing `task_id = <spec-id>.N` rule) |
| branch | same as canonical id |
| bare aliases | `wor-17` / `gh-123` / `gl-456` (and `.M`) — resolve exactly as `fn-52` / `fn-52.M` expand to the full-slug id today |

| `tracker.type` | Native identifier | Minted id |
|---|---|---|
| `linear` / `jira` | `WOR-17` / `PROJ-123` | `wor-17-slug` / `proj-123-slug` (native `KEY-N`) |
| `github` | `#123` | `gh-123-slug` (synthetic; reserved while type is github) |
| `gitlab` | `<project>#456` | `gl-456-slug` (synthetic; project-scoped `iid`) |

Create it with:

```bash
$FLOWCTL spec create --tracker-first --tracker-identifier "WOR-17" --title "<issue title>" --json
# GitHub: --tracker-identifier "#123" → gh-123-slug
# GitLab: --tracker-identifier "group/project#456" → gl-456-slug
```

`--tracker-first` keys the spec by the tracker identifier instead of allocating a fresh `fn-NN`. No second id; no rename. Skills route here when `tracker.specIds=tracker` and the bridge is active.

### Flow-first — keep `fn-NN`, gain a resolvable alias

A spec authored in flow (capture/interview/plan) keeps its sequential `fn-NN-slug` handle (project convention preserved). On push, the tracker key is stored in the single `tracker.identifier` field (R4) as a **resolvable alias**:

```bash
$FLOWCTL sync set-tracker-id "fn-42-foo" "$ISSUE_UUID" --identifier "WOR-99" --url "$ISSUE_URL"
```

Now `work wor-99`, `show wor-99`, etc. resolve to `fn-42-foo` **without renaming it**. The issue carries the flow id back via a **`flow:fn-42-foo` label** — the *primary, linkify-safe* back-reference (label text is never auto-linkified). A `[fn-42-foo]` title prefix is an optional secondary; avoid it when the flow id carries a tracker key (e.g. a tracker-first `wor-21-slug`), since the tracker auto-linkifies the key substring in the title — see the "Linkify hazard" note in [comments-sync.md](comments-sync.md). Body-embedded back-references (HTML comments) suffer the same mangle; the label is the durable form.

## Resolution (fn-52.10 — the scaffold calls it, never reimplements it)

- The tracker key is a **first-class, resolvable handle**, not just a stored label: `work wor-17`, `plan wor-17`, `show wor-17`, tasks `wor-17.M` all resolve. flowctl widened `is_spec_id` / `expand_bare_spec_id` so every command inherits resolution.
- **Case:** `tracker.identifier` stores the display form (`WOR-17`); the canonical id derives from the lowercase key (`wor-17-slug`); alias resolution is case-insensitive.
- The native `fn-` prefix is reserved for the sequential scheme; tracker-key resolution is tried only after the `fn-` path misses. Enumeration sees tracker-key specs, but native `fn-N` allocation counts `fn-*` only — a `wor-9999` never bumps the next `fn`.
- **One tracker team / workspace per repo** — the bridge assumes a single team key so a bare `wor-17` resolves unambiguously. Cross-workspace same-key collision (two teams both keyed `WOR`) is out of scope and not disambiguated.

> The id-grammar widening had to cover the FULL command surface, not just the named lifecycle commands (memory: `id-grammar-widening-must-cover-the-full`). That work is fn-52.10's; the scaffold relies on it being complete and only calls `flowctl <cmd> wor-17`.

## Create-first - issue exists before the local id (R19)

When `tracker.specIds=tracker` and no issue exists yet, the caller cannot mint a tracker-keyed id without a key. **Create-first** (steps.md Phase 2d) creates the issue first and returns `{id, identifier, url}` with **no local spec id as input**. Attach is still via `set-tracker-id` after mint - create-first does not write sync state itself.

Sequence (owned by the calling skill; tracker-sync owns only the create-first op):

1. `create-first(title, body)` → `{id, identifier, url}` (adapter-native identifier: `WOR-17` / `PROJ-123` / `#123` / `<project>#<iid>`).
2. Mint: `spec create --tracker-first --tracker-identifier <identifier>` → `KEY-N-slug` or synthetic `gh-N-slug` / `gl-N-slug` (flowctl mint; this file does not reimplement synthesis).
3. Attach: `sync set-tracker-id <spec-id> <id> --identifier <identifier> --url <url>`.
4. Seed merge base (both halves) so the first reconcile is not a whole-body conflict - same first-link base-seeding as Phase 2b.

**Pre-spec recovery:** at create-first time no local spec id exists, so `sync receipt` cannot run yet. Durable recovery lives at `.flow/create-first/<retryKey>.json` keyed by:

```
retryKey = sha256(tracker.type + "\0" + title + "\0" + body)[:16]
```

A retry after partial failure (remote create ok, local mint fail) finds that file and **links** the existing issue - never creates a second one. Normal `sync receipt <spec-id>` runs only after mint + attach; then the recovery file is consumed. Full contract: [steps.md](../steps.md) Phase 2d.

## Hard rules — never violate

- **No rename-on-push.** Existing spec/task ids, branches, and dep edges are never mutated when a spec is synced; the tracker key is added as a resolvable handle/alias, not a replacement.
- **`spec set-title` on a tracker-linked spec updates the title only** — the canonical id, branch, and files are never re-slugged. A renamed id after a title change has broken this and desynced the linkage. Unlinked specs keep today's rename behavior.
- **Surface `identifier` in sync listings** so users see both handles (the canonical flow id and the board-facing `WOR-17`).
- **Create-first never renames and never mints.** It returns the adapter identifier as-is; the caller mints and attaches. A retry never creates a second issue (recovery file + retry lookup key).
- This is **additive** — it does not require the separate `fn-NN`-deprecation id-scheme change to land first; that change, when it comes, only governs *removing* `fn-NN`, not *also accepting* the tracker key.
