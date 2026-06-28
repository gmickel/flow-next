# Transport-adapter interface + normalized payload contract

This is the **contract** between the transport-blind orchestration skeleton ([../SKILL.md](../SKILL.md), [../steps.md](../steps.md)) and the per-tracker adapters. It is the spine of fn-52.2 — the later tasks plug into it without reshaping it:

- **Transports** (fn-52.3 Linear, fn-52.7 GitHub, fn-69 GitLab) implement the interface methods below, each mapping its wire shape to/from the **normalized structs**.
- **Reconcile** (fn-52.4 body, fn-52.5 status/comments) operates ONLY on the normalized structs — it never sees a Linear/GitHub/GitLab wire detail. This is what makes the 3-way merge transport-blind and testable.
- **Dependency projection** (fn-64) adds two relation methods (`setIssueRelation` / `listIssueRelations`) on the same firewall: the skill resolves `depends_on_epics` edges into (current-issue, dep-issue) pairs and calls the normalized relation transport; each adapter (fn-64.3 Linear, fn-64.4 GitHub, fn-69 GitLab) implements it at its own fidelity. The skill never branches on tracker type (R8).

The structs are the firewall: a transport bug stays in the adapter; a merge bug stays in reconcile.

## Transport interface

Nine methods. Each adapter (Linear via MCP-or-GraphQL; GitHub via `gh`; GitLab via `glab` CLI → raw-REST token fallback) implements all nine. The skeleton calls them by name and never branches on tracker type — the active adapter (from `tracker.type`) supplies the implementation.

| Method | Direction | Input | Output | Implemented by |
|---|---|---|---|---|
| `fetchIssue(trackerId)` | tracker → flow | UUID | normalized `issue` (or `not-found` / `errored`) | fn-52.3 / fn-52.7 / fn-69 |
| `writeIssue(issue)` | flow → tracker | normalized `issue` (create if no id, else update) | `{id, identifier, url}` | fn-52.3 / fn-52.7 / fn-69 |
| `listComments(trackerId)` | tracker → flow | UUID | normalized `comment[]` | fn-52.3 / fn-52.7 / fn-69 |
| `postComment(trackerId, body)` | flow → tracker | UUID + markdown body | normalized `comment` | fn-52.3 / fn-52.7 / fn-69 |
| `readStatus(trackerId)` | tracker → flow | UUID | normalized `status` | fn-52.3 / fn-52.7 / fn-69 |
| `setStatus(trackerId, status)` | flow → tracker | UUID + normalized `status` | ok / `errored` | fn-52.3 / fn-52.7 / fn-69 |
| `listIssueRelations(issue)` | tracker → flow | the `issue` to inspect | normalized `relation[]` (or `errored`) | fn-64.3 / fn-64.4 / fn-69 |
| `setIssueRelation(issue, blockedBy)` | flow → tracker | the `issue` + the issue it is **blocked by** | ok / `errored` / `noop` | fn-64.3 / fn-64.4 / fn-69 |
| `listOpenIssues(filter)` | tracker → flow | a `filter` (the promoted-lane `readyState`) | normalized `issue[]` (or `noop` / `errored`) | fn-68.2 (Linear + GitHub) / fn-69 (GitLab) |

`listIssueRelations` / `setIssueRelation` are the **dependency-projection** pair added by fn-64 — see [Relation transport](#relation-transport-dependency-projection-fn-64) below. `listOpenIssues` is the **enumeration** method added by fn-68 — see [Enumeration transport](#enumeration-transport-listopenissues-fn-68) below. The first six are unchanged.

**Contract rules every adapter MUST honor:**

- **Map to/from the normalized structs at the adapter boundary.** Reconcile never receives a wire shape. A new tracker (Jira/Notion later) is a new adapter, not a reconcile change.
- **`fetchIssue` on a missing / archived / deleted issue returns `not-found` (or `errored`), never raises.** The skeleton then emits an `errored` receipt and does NOT mutate state (no `lastSyncedAt` advance) — a failed fetch never corrupts the merge base.
- **`writeIssue` is upsert:** no `id` on the input ⇒ create (returns the new id/identifier/url); `id` present ⇒ update. (Linear's official MCP uses upsert verbs `save_issue`/`save_comment`, not `create_*`/`update_*` — pinned at build in fn-52.3.)
- **No-transport path:** when no transport is reachable (`tracker.type` set but MCP absent AND `LINEAR_API_KEY` absent; or `gh` not authed; or GitLab with no `glab` credential AND no `GITLAB_TOKEN`/`CI_JOB_TOKEN`), every method is a documented `noop` + receipt note — never a crash. Same detect-best-available shape as fn-51's driver ladder.
- **Transport is recorded on every receipt** (`--transport mcp|graphql|gh|glab|rest|none`) — `glab` (GitLab `glab` CLI rung) and `rest` (GitLab raw-REST `/api/v4` token fallback) are the GitLab rungs; `none` is the universal no-op rung.

## Normalized payload structs

The wire-agnostic shapes the transports produce and reconcile consumes. These are conceptual JSON shapes (the host agent passes them as data; flowctl persists only the bits it owns — id, identifier, url, merge-base snapshot, `lastSyncedAt`).

### `issue`

```jsonc
{
  "tracker":   "linear",            // linear | github | gitlab  (which adapter produced this)
  "type":      "issue",             // tracker's item type (issue / ticket)
  "id":        "uuid-or-null",      // durable id dedupe key (Linear id; GH node id; GitLab global issue id). null on a create.
  "identifier":"WOR-17",            // display key (Linear identifier; GH "#123"; GitLab "<project>#<iid>"). Surfaced in listings.
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
  "marker":    "flow-evt:work.done",// dedup/echo marker: present on EVERY flow-OWNED comment so a
                                    // pull doesn't re-import flow's own structured comment. null on
                                    // genuine tracker-side comments (those pull into the spec sync log).
                                    // The adapter sets `marker` from ANY flow-owned marker line (see the
                                    // marker-vocabulary table below) — NOT only `flow-evt:<event>`.
  "parentId":  "uuid-or-null",      // OPTIONAL reply/parent metadata (fn-68 R15). On a THREADED tracker
                                    // (Linear) a reply carries its parent comment's id, so a human's
                                    // answer-under-a-question is matched by thread + the question-valve
                                    // `id`. On a FLAT tracker (GitHub — no threads) there is no parent,
                                    // so parentId is null and the `<!-- flow-next:answer id=<hash> -->`
                                    // body marker is the load-bearing match (by id, threading-blind).
  "authorAuthority": "writer|outsider|bot|unknown" // fn-68 R15 SECURITY: the author's permission tier —
                                    // the answer valve honors a `flow-next:answer` marker ONLY from a
                                    // `writer` (a marker id alone is NOT proof; anyone with comment access
                                    // could inject the marker). GitHub: derived from `author_association`
                                    // (OWNER/MEMBER/COLLABORATOR ⇒ writer; CONTRIBUTOR/FIRST_TIMER/NONE ⇒
                                    // outsider; a `*[bot]` login ⇒ bot). Linear: team membership ⇒ writer,
                                    // guest/none ⇒ outsider. GitLab: project membership `access_level`
                                    // (≥30 Developer ⇒ writer; <30 / no membership ⇒ outsider; a bot/service
                                    // account ⇒ bot). `unknown` when the transport can't resolve it
                                    // ⇒ treated as NOT authorized (fail closed).
}
```

> **`parentId` is OPTIONAL and additive (fn-68 R15).** It exists ONLY to let the
> async question-valve match a human's *answer* reply to the *question* comment by
> `id`. Adapters on a threaded tracker (Linear) populate it from the reply/parent
> link; flat trackers (GitHub) leave it `null` and the answer is matched purely by
> the `<!-- flow-next:answer id=<hash> -->` marker. Reconcile/dedup (comments-sync)
> is unaffected when `parentId` is absent — the field is read only by the
> question-valve answer round-trip ([steps.md](../steps.md) Phase 7).

**Marker vocabulary the adapter MUST recognize (fn-68 R15 — read-side).** Every
adapter's `listComments` sets `comment.marker` from the FIRST flow-owned marker
line it finds — **not only `flow-evt:<event>`**. The flow-owned set is closed and
shared by Linear (MCP + GraphQL), GitHub, and GitLab; an adapter that detects only the
lifecycle marker would return a parked **question** with `marker: null`, and
comments-sync would wrongly import it into `## Sync Log`. The vocabulary:

| Body marker line | `comment.marker` | Pull behavior |
|---|---|---|
| `<!-- flow-next:sync … evt=<event> … -->` | `flow-evt:<event>` | flow-OWNED echo — skip Sync-Log import (Layer 1) |
| `<!-- flow-next:question id=<hash> status=… -->` | `flow-evt:question` | flow-OWNED — skip Sync-Log import; the question's home is `## Open Questions` / the tracker, never the Sync Log |
| `<!-- flow-next:status … rolling -->` | `flow-evt:status` | flow-OWNED rolling status comment — skip Sync-Log import |
| `<!-- flow-next:answer id=<hash> -->` | **`null`** (genuine human content) — BUT carries the answer `id` for the round-trip | the question-valve answer round-trip ([steps.md](../steps.md) Phase 7) consumes it **by `id` BEFORE** the generic Sync-Log append; an answer that matches no open question falls through to a normal Sync-Log comment |
| (no flow marker) | `null` | genuine tracker comment → `## Sync Log` |

> **`flow-next:answer` is the one human-authored marker** — it is NOT a flow echo,
> so `marker` stays `null` (it is genuine tracker-side content the human wrote). The
> adapter still **surfaces its `id`** (parse `flow-next:answer id=<hash>`) so the
> round-trip can pair it; the round-trip is what claims it before the Sync-Log
> append, NOT the marker skip. Keeping `marker: null` is deliberate — a matched
> answer is imported under `## Open Questions` (not the Sync Log), and an *unmatched*
> answer is a real comment that SHOULD reach the Sync Log.

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

**Transport-blind terminal invariant (R1, R8).** A **terminal outbound write** (mapping a spec to normalized `done`/`verified`, i.e. closing/completing the tracker issue) **requires merge evidence**: the flow→normalized map is `flowToNormalized(spec, prEvidence)` ([status-sync.md](status-sync.md)) and emits a terminal status ONLY when a `MERGED` PR probe for the spec branch is present. Local completion (spec `done` + completion review shipped) is necessary, not sufficient. This invariant is **transport-blind** — every adapter (Linear fn-52.3, GitHub fn-52.7, GitLab fn-69, any future tracker) receives a terminal normalized status only after the gate, and maps it DOWN to its native closed state without re-deciding. No adapter ever closes an issue from local spec state alone.

### `relation`

The wire-agnostic edge shape `listIssueRelations` produces. One entry per directed blocked-by edge the transport can see for the inspected issue.

```jsonc
{
  "from":   "uuid-or-identifier",   // the BLOCKED issue (the one that depends on `to`)
  "to":     "uuid-or-identifier",   // the BLOCKING issue (the dependency / blocker)
  "type":   "blocks",               // always "blocks" — flow only projects the blocked-by edge type
  "source": "flow",                 // flow | human | unknown | block-only — provenance WHERE the transport can tell;
                                    // else the flow-side `depRelations` ledger is authoritative (see below)
  "linkPresent": true               // is the edge backed by a TRACKER-VISIBLE link right now? false ⇒ orphaned
                                    // provenance (e.g. GitLab `block-only`: in the flow block, link removed) — a
                                    // human-removal signal, NOT a satisfied projection. Consumers branch on this.
}
```

- **`from` / `to` are the directed edge `from` is-blocked-by `to`.** This is the one direction convention every adapter maps to consistently (see [Direction convention](#direction-convention) below). The identifier form (UUID vs `#N` display key) is whatever the transport natively returns; the skill matches against the resolved pair, not on form.
- **`type` is always `blocks`.** Flow projects exactly one edge kind — the blocked-by relation. An adapter that surfaces other relation kinds (`relates`, `duplicate`, …) MUST NOT return them here; this list is the blocked-by view only, so the skill's read-before-write dedup never trips over an unrelated edge.
- **`source` distinguishes ours-vs-theirs only where the transport records it.** Linear's native relations, GitHub's native dependencies, and GitLab's native issue links do **not** store authorship, so on those rungs `source` is `unknown` and the flow-side `depRelations` ledger (fn-64.1) is the authority for "did flow create this?". Wherever the `<!-- flow:deps -->` block lives — GitHub's fenced fallback (native deps unavailable) or GitLab on every tier (the durable provenance source alongside the native `is_blocked_by` link, and the sole record on the Free/personal `relates_to` degrade) — the marker itself is the provenance boundary (lines inside `<!-- flow:deps -->` … `<!-- /flow:deps -->` are flow's, `source: "flow"`). Either way, **provenance is never inferred from `source` alone** — the ledger / marker is load-bearing. (GitLab note: a directionless `relates_to` link — written for UI visibility when `is_blocked_by` is unlicensed — carries **no** from/to direction, so `listIssueRelations` NEVER derives a `blocks` edge from it; direction comes only from a native directional link or the `<!-- flow:deps -->` block.)
- **`linkPresent` separates a live projection from orphaned provenance — EVERY producer MUST set it (required field, not optional).** `source` says *who authored* the edge; `linkPresent` says *whether the tracker still shows it as a link right now*. **Set `true`** on every rung where the returned relation IS the visible projection: Linear native relations, GitHub native dependencies, **and** GitHub's fenced `#N` block (its reduced rung has no separate native link, so the block is the sole projection — nothing can orphan). **`false` is GitLab-only:** GitLab uniquely writes a native link (`is_blocked_by` / degraded `relates_to`) **and** a separate `<!-- flow:deps -->` block on every tier, so the two can diverge — an edge in the block whose tracker-visible link a human deleted returns `linkPresent: false` (GitLab tags it `source: "block-only"`). The read-before-write dedup and the reconcile **collision** rule (status-sync.md / steps.md) MUST branch on `linkPresent` — never bare membership — so a removed board-visible link is detected as a human-removal collision — **queued, default NOT re-created** (autonomous `sync defer`; interactive surface/ask; never silently re-create — that steamrolls a deliberate removal, R6/R10), not silently masked by the still-present block. A producer that omits `linkPresent` would make every Linear/GitHub live relation read as falsy → misclassified as orphaned: the field is mandatory on all of them.

## Relation transport (dependency projection, fn-64)

`depends_on_epics` edges between linked specs project to **blocked-by** relations between their tracker issues. The skill (fn-64.5) resolves each edge to a (current-issue, dep-issue) pair and drives this transport pair; each adapter implements it at its native fidelity (Linear native relations — fn-64.3; GitHub native dependencies or a fenced body block — fn-64.4; GitLab native `is_blocked_by` issue links on a licensed namespace, else a directionless `relates_to` for UI visibility **plus** the fenced `<!-- flow:deps -->` body block for direction/provenance — fn-69).

### Direction convention

Stated once, mapped consistently by every adapter:

> **blocked-by = "the current issue is blocked by the dependency issue."**

Flow's `depends_on_epics: [B]` on spec A means *A depends on / is blocked by B*. The projected edge is therefore `from = A's issue` (blocked), `to = B's issue` (blocker), `type = "blocks"`. This matches the fn-64.1 ledger's directed `from_tracker_id → to_tracker_id` pair and `setIssueRelation(issue=A, blockedBy=B)`. Adapters translate to their wire form: Linear `issueRelationCreate(type: blocks)` with operands ordered so the blocker blocks the blocked; GitHub `…/issues/{A}/dependencies/blocked_by` pointing at B; GitLab `POST /issues/{A}/links` with `link_type=is_blocked_by` pointing at B (licensed namespace) — on a 403 the fenced block carries the direction; the fenced block lists B as a `#N` "Blocked by" entry under A's body. There is no inversion ambiguity — every rung anchors on this one sentence.

### Read-before-write idempotency (mandatory)

**No platform reliably no-ops a duplicate relation**, so every adapter MUST `listIssueRelations(issue)` and check for the (from, to) pair **before** calling `setIssueRelation`. Skip the write when the edge already exists. The Linear dedup must canonicalize across **both** `relations` and `inverseRelations` (the same edge appears from either endpoint) before comparing; the GitHub fenced-block writer must not append a `#N` already present in the block; the GitLab adapter dedups on the **tracker-visible link** — the existing `/links` listing (native `is_blocked_by`, or degraded `relates_to`). The `<!-- flow:deps -->` block GitLab carries on every tier is **provenance, NOT dedup proof**: a block entry whose link is **gone** is a human-removal collision — **queued, default NOT re-created** (`sync defer` autonomous; surface/ask interactive; never silently re-create, R6/R10) — never an already-projected no-op masked by the block. A re-run over a still-**linked** dependency creates zero new relations and appends nothing (R3).

### Never-delete-non-ours provenance (mandatory)

`setIssueRelation` only ever **creates** the blocked-by edge — it never removes a relation. A relation tracker-sync cannot **prove** it created is never touched (R6):

- **Native relations (Linear, GitHub-native deps, GitLab native issue links):** provenance lives in the flow-side `depRelations` ledger — `flowctl sync set-dep-relation` records the directed `{key, dep_spec, from_tracker_id, to_tracker_id, type: "blocks", source: "flow", updatedAt}` entry per projected edge (fn-64.1). An edge not in the ledger is, by definition, not ours and is left alone.
- **Fenced `<!-- flow:deps -->` block (GitHub's fenced fallback when native deps are unavailable; GitLab on every tier — it carries the block as the durable direction/provenance source alongside the native `is_blocked_by` link, and as the sole direction record on the Free/personal `relates_to` degrade):** the `<!-- flow:deps -->` … `<!-- /flow:deps -->` marker is the provenance boundary — only `#N` lines **inside** the marker are flow's. The body-merge layer ([body-merge.md](body-merge.md)) excludes that fenced region from divergence detection so a reconcile never folds flow's own block back into the spec, and a `writeIssue` UPDATE preserves it on every write that carries it (fn-64.5 owns the exclusion rule).

This mirrors the bridge's existing "surface diffs, never overwrite" posture: the cost of silently deleting a human's manual relation is high, so projection stays strictly additive over edges it can prove are its own.

### Transport-unavailable / completed-blocker

- **No transport reachable** → the projection is a documented `noop` + receipt note (same no-transport shape as the six core methods), never a crash and never a lifecycle block.
- **Completed blocker** (dep spec is locally `done`) → the relation stays visible on the tracker as a historical blocker; it is NOT removed and does NOT feed back into `ready=true` gating. The completed-blocker decision is the skill's (fn-64.5), keyed off the **local** dep-spec status (`dep_status` from `flowctl sync list-dep-relations`), not a remote fetch.

## Enumeration transport (`listOpenIssues`, fn-68)

Backlog mode ([../../flow-next-pilot](../../flow-next-pilot/SKILL.md)) must **union in tracker issues that have no flow spec** — tickets a human promoted on the board but never `capture`/`interview`'d into a spec, invisible to `flowctl specs`. The six core methods are all **per-issue** (you already hold the id); none can *enumerate*. fn-68 adds one transport-blind method.

### `listOpenIssues(filter) → issue[]`

| | |
|---|---|
| **Direction** | tracker → flow |
| **Input** | a `filter` — for v1 the single field `{ readyState: <tracker.readyState> }` |
| **Output** | normalized `issue[]` (the same `issue` struct above), or `noop` (no-transport / readyState unset) / `errored` |
| **Implemented by** | fn-68.2 — **Linear** ([linear-graphql.md](linear-graphql.md) / [linear-mcp.md](linear-mcp.md)) + **GitHub** ([github.md](github.md)); **GitLab** ([gitlab.md](gitlab.md)) implements it (fn-69); Jira (fn-70) inherits the contract |

**Exact-match filter (mandatory).** `listOpenIssues` lists open issues at the **exact** `tracker.readyState` state/label — the **promoted lane**, not the whole issue history:

- **Linear** — issues whose workflow-state **name** equals `readyState` (case-insensitive/trimmed, the same match as the readiness projection in [status-sync.md](status-sync.md)). No `state.type` ordering, no "and-later" states.
- **GitHub** — open issues carrying the `readyState` **label** (case-insensitive). No label ordering.
- **GitLab** — open issues (`state=opened`) carrying the exact `readyState` **label** (case-insensitive) — `glab issue list --state opened` / REST `GET /projects/:id/issues?state=opened&labels=<readyState>`. No label ordering. (GitLab, like GitHub, has no rich workflow — readiness is a label, not a workflow state.)

**`readyState` matching is exact — there is no state ordering, so "beyond" / "and-later" is undefined** (an explicit ordered promoted-set is a future config knob, **never inferred** by an adapter). The skill (steps.md Phase 7a) — not the adapter — owns the policy of what to do with the result; the adapter only enumerates the exact lane.

**Contract rules (mirroring the other methods):**

- **`tracker.readyState` unset ⇒ documented `noop` (return `[]`), never an error.** No promoted lane exists to filter on — backlog mode falls back to flow-ready specs only. The **skill** ([steps.md](../steps.md) Phase 7a) short-circuits to the no-op + note before calling the transport; an adapter that *is* reached with an empty filter likewise returns `[]` + `noop`.
- **No transport reachable ⇒ `noop` + receipt note, `[]`** — same no-transport floor as the other methods.
- **Returns normalized `issue` structs** (transport-blind). The skill reads `{id, identifier, title, status, labels, url}` and never sees a Linear/GitHub/GitLab wire shape — exactly like `fetchIssue`. A tracker-only ticket (no flow spec) has the same `issue` shape as a linked one. **Linkage is determined authoritatively by the local sync state** (the tracker-ids the skill recorded as linked), **NOT** by the presence/absence of a `flow:<id>` label — the label is a corroborating hint only. A bounded/truncated label set is **never** read as "unlinked" (a many-label issue could carry the back-reference past the connection bound), so a linked issue is never mis-classified as tracker-only.
- **Read-only — never advances `lastSyncedAt`** (an enumeration is not a reconcile). Its receipt is a `noop`-status read note.

## Why structs, not byte-copy

The flow spec is **structured** (sections, R-IDs, source tags); the tracker issue body is **free-form**. The adapter normalizes the tracker side into these structs; reconcile (fn-52.4) does a semantic 3-way merge against the stored merge base and **translates** between the two formats (flow→tracker renders/cleans the structure into a readable issue; tracker→flow folds free-text edits into the right flow sections without inventing R-IDs/tags). The structs are the seam that keeps that translation testable: "given these two normalized `issue`s and this base, does the merge preserve both sides' non-conflicting changes?" is answerable without a live tracker.
