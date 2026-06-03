# Transport-adapter interface + normalized payload contract

This is the **contract** between the transport-blind orchestration skeleton ([../SKILL.md](../SKILL.md), [../steps.md](../steps.md)) and the per-tracker adapters. It is the spine of fn-52.2 — the later tasks plug into it without reshaping it:

- **Transports** (fn-52.3 Linear, fn-52.7 GitHub) implement the six interface methods below, each mapping its wire shape to/from the **normalized structs**.
- **Reconcile** (fn-52.4 body, fn-52.5 status/comments) operates ONLY on the normalized structs — it never sees a Linear/GitHub wire detail. This is what makes the 3-way merge transport-blind and testable.

The structs are the firewall: a transport bug stays in the adapter; a merge bug stays in reconcile.

## Transport interface

Six methods. Each adapter (Linear via MCP-or-GraphQL; GitHub via `gh`) implements all six. The skeleton calls them by name and never branches on tracker type — the active adapter (from `tracker.type`) supplies the implementation.

| Method | Direction | Input | Output | Implemented by |
|---|---|---|---|---|
| `fetchIssue(trackerId)` | tracker → flow | UUID | normalized `issue` (or `not-found` / `errored`) | fn-52.3 / fn-52.7 |
| `writeIssue(issue)` | flow → tracker | normalized `issue` (create if no id, else update) | `{id, identifier, url}` | fn-52.3 / fn-52.7 |
| `listComments(trackerId)` | tracker → flow | UUID | normalized `comment[]` | fn-52.3 / fn-52.7 |
| `postComment(trackerId, body)` | flow → tracker | UUID + markdown body | normalized `comment` | fn-52.3 / fn-52.7 |
| `readStatus(trackerId)` | tracker → flow | UUID | normalized `status` | fn-52.3 / fn-52.7 |
| `setStatus(trackerId, status)` | flow → tracker | UUID + normalized `status` | ok / `errored` | fn-52.3 / fn-52.7 |

**Contract rules every adapter MUST honor:**

- **Map to/from the normalized structs at the adapter boundary.** Reconcile never receives a wire shape. A new tracker (Jira/Notion later) is a new adapter, not a reconcile change.
- **`fetchIssue` on a missing / archived / deleted issue returns `not-found` (or `errored`), never raises.** The skeleton then emits an `errored` receipt and does NOT mutate state (no `lastSyncedAt` advance) — a failed fetch never corrupts the merge base.
- **`writeIssue` is upsert:** no `id` on the input ⇒ create (returns the new id/identifier/url); `id` present ⇒ update. (Linear's official MCP uses upsert verbs `save_issue`/`save_comment`, not `create_*`/`update_*` — pinned at build in fn-52.3.)
- **No-transport path:** when neither transport is reachable (`tracker.type` set but MCP absent AND `LINEAR_API_KEY` absent, or `gh` not authed), every method is a documented `noop` + receipt note — never a crash. Same detect-best-available shape as fn-51's driver ladder.
- **Transport is recorded on every receipt** (`--transport mcp|graphql|gh|none`).

## Normalized payload structs

The wire-agnostic shapes the transports produce and reconcile consumes. These are conceptual JSON shapes (the host agent passes them as data; flowctl persists only the bits it owns — id, identifier, url, merge-base snapshot, `lastSyncedAt`).

### `issue`

```jsonc
{
  "tracker":   "linear",            // linear | github  (which adapter produced this)
  "type":      "issue",             // tracker's item type (issue / ticket)
  "id":        "uuid-or-null",      // durable UUID dedupe key (Linear id; GH node id). null on a create.
  "identifier":"WOR-17",            // display key (Linear identifier; GH "#123"). Surfaced in listings.
  "title":     "string",
  "body":      "free-form markdown",// the issue body — free-form on the tracker side
  "status":    { "raw": "In Review", "normalized": "in-review" },   // a status struct (see below)
  "priority":  "string-or-null",    // tracker's priority label (folded, never auto-changed — R7)
  "labels":    ["flow:fn-42-foo", "..."],  // includes the flow back-reference label
  "url":       "https://...",
  "updatedAt": "ISO-8601"           // tracker-side modified time (drives staleness / echo-suppression)
}
```

### `comment`

```jsonc
{
  "id":        "uuid",
  "author":    "string",            // tracker-side author (for the sync log)
  "body":      "markdown",
  "createdAt": "ISO-8601",
  "marker":    "flow-evt:work.done" // dedup/echo marker: present on flow-posted comments so a
                                    // pull doesn't re-import flow's own structured comment. null on
                                    // genuine tracker-side comments (those pull into the spec sync log).
}
```

### `status`

```jsonc
{
  "raw":        "In Review",        // the tracker's literal workflow-state name (team-specific)
  "normalized": "in-review"         // mapped to a flow-stable vocabulary (see below)
}
```

**Normalized status vocabulary** (the stable middle the who-wins rules in fn-52.5 reason over — tracker workflow-state names are team-specific and map INTO this; the exact map is config-driven via `tracker.perTracker`):

`backlog` · `planned` · `in-progress` · `in-review` · `done` · `verified` · `deferred` · `wontfix`

Who-wins (R7, implemented in fn-52.5 — [status-sync.md](status-sync.md)): tracker wins `done`/`verified`; flow wins `in-progress`; `priority` + `deferred`/`wontfix` surface to the user, never auto-changed. Comments/evidence two-way append + dedup (R8) is [comments-sync.md](comments-sync.md).

## Why structs, not byte-copy

The flow spec is **structured** (sections, R-IDs, source tags); the tracker issue body is **free-form**. The adapter normalizes the tracker side into these structs; reconcile (fn-52.4) does a semantic 3-way merge against the stored merge base and **translates** between the two formats (flow→tracker renders/cleans the structure into a readable issue; tracker→flow folds free-text edits into the right flow sections without inventing R-IDs/tags). The structs are the seam that keeps that translation testable: "given these two normalized `issue`s and this base, does the merge preserve both sides' non-conflicting changes?" is answerable without a live tracker.
