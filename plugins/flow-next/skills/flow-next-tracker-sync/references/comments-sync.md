# Comments / evidence reconciliation — two-way append + dedup (R8)

The comments-sync reconcile body behind the [../steps.md](../steps.md) `push` /
`pull` / `reconcile` hooks (`postComment` / `listComments`). It syncs **comments and
evidence two-way, append-only**: flow lifecycle events post structured comments to
the issue; tracker-side comments pull into the spec's sync log. Because both
directions are **appends, there is no merge conflict** (unlike the body) — the whole
problem is **dedup**: never post the same flow comment twice, never re-import a
human-pasted copy of a flow comment.

It operates ONLY on the normalized `comment` struct
([adapter-interface.md](adapter-interface.md)); the transport
([linear-ladder.md](linear-ladder.md)) is the firewall, this file is the dedup +
append policy.

> **Append-only is the contract.** Comments are never edited or deleted by the
> bridge. The ONE narrow exception is a single, clearly-marked, opt-in flow-owned
> "flow-next status" rolling comment (one per issue, updated in place via its
> marker) — described last, and explicitly bounded so it never weakens the
> append-only rule for evidence / lifecycle / user comments. If the rolling comment
> adds complexity, drop it and append; the append-only contract for every other
> comment is non-negotiable.

> **Live-verification status (this environment).** Posting a comment to / listing
> comments from a real Linear issue needs live credentials — unavailable in the
> build environment. The **strictly-live `postComment` / `listComments` round-trip
> is deferred to the post-PR smoke-testing phase** the maintainer drives (same
> posture as the [linear-ladder.md](linear-ladder.md) round-trip spike,
> [body-merge.md](body-merge.md), and [status-sync.md](status-sync.md)). Everything
> else here — the marker format, the three-layer dedup, the normalized-text hash,
> the lifecycle-event → comment mapping — is a complete, runnable procedure with
> worked fixtures and explicit oracles below, exercisable without a live tracker.

## Two directions, both append-only

| Direction | What flows | Mechanism |
|---|---|---|
| **flow → tracker** | a structured comment per opted-in lifecycle event (work done + evidence, make-pr URL, completion-review verdict, …) | `postComment(trackerId, body-with-marker)` |
| **tracker → flow** | genuine tracker-side comments (a PM's question, a reviewer's note) | `listComments(trackerId)` → fold into the spec's `## Sync Log` |

Neither direction overwrites the other; both are appends. The skill posts/pulls only
for the events opted in via `tracker.perEvent.<event>` set to `comment` (or an event
whose policy implies a comment, e.g. `work.done` → status comment + evidence). With
every `perEvent` leaf defaulting to `off`, **nothing is posted until a user opts in**
(spec Boundaries).

### Which lifecycle events post a comment (R8 / R10)

The R10 lifecycle touchpoints (wired into the 7 skills in fn-52.6) that produce a
**comment** here:

| Event (`tracker.perEvent` key) | Comment posted to the issue |
|---|---|
| `work.done` | a status comment + **evidence** (tests run, PR link if present) |
| `makePr` | **link** the PR to the issue (not just a comment) so it renders as a reviewable diff: make-pr §4.6a adds a non-closing `Ref <identifier>` to the PR body (→ the tracker integration auto-links it → **Linear Diffs**); the Linear/GraphQL rung also creates the rich PR attachment via `attachmentLinkURL`. GitHub tracker → native `Refs #N`. See [linear-ladder.md](linear-ladder.md) / [github.md](github.md). |
| `resolvePr` | an optional resolution-summary comment |
| `completionReview` | the completion-review verdict + R-ID coverage summary |

`work.firstClaim` typically drives a **status change** (→ in-progress, see
[status-sync.md](status-sync.md)), not a comment — but MAY also post a one-line
"work started" comment if the user set that event to `comment`. `capture` /
`interview` / `plan` primarily sync the **body** ([body-merge.md](body-merge.md));
they post a comment only when explicitly opted into `comment`.

The actual wiring (calling this reconcile from each skill's lifecycle hook) is
**fn-52.6**; this file defines the comment shape + dedup the wiring relies on.

## Dedup — the whole problem (R8)

Appends don't conflict, but a naive re-sync re-posts everything. Three independent
layers, checked in order; **any** hit ⇒ skip the post/import:

### Layer 1 — the embedded marker (primary, exact)

Every flow-posted comment carries a **hidden HTML-comment marker** as its first
line. The marker is the canonical dedup key and the back-reference all at once:

```html
<!-- flow-next:sync issue=<issue-uuid> spec=<spec-id> evt=<event> evidence=<sha-or-none> -->
```

- `issue=<issue-uuid>` — the tracker issue's stable UUID. **Primary, linkify-safe
  dedup key** (a UUID is not an issue-key pattern, so trackers never rewrite it —
  see "Linkify hazard" below). Match on `issue` + `evt` + `evidence`.
- `spec=<spec-id>` — the flow spec this comment belongs to (e.g. `fn-42-add-oauth`
  or `wor-17-slug`). **For readability + the back-reference only — never the sole
  match key.** A tracker-first id (`wor-17-slug`) embeds the tracker key, which the
  tracker auto-linkifies (next note), mangling a literal `spec=` match.
- `evt=<event>` — the lifecycle event (`work.done`, `makePr`,
  `completionReview`, …) — the **shorthand the adapter surfaces as the normalized
  `comment.marker` (`flow-evt:<event>`)**.
- `evidence=<sha>` — for an evidence comment, the commit/evidence sha it reports
  (`none` when not evidence-bearing). This makes a *re-post of the same evidence*
  detectable even if the surrounding prose changed.

> **Marker reconciliation.** The adapter ([linear-ladder.md](linear-ladder.md),
> [linear-mcp.md](linear-mcp.md), [linear-graphql.md](linear-graphql.md)) detects
> the `flow-evt:<event>` token and sets the normalized `comment.marker` field. This
> file's richer HTML-comment form (`<!-- flow-next:sync … -->`) is what is actually
> *written into the body*; the adapter's `flow-evt:<event>` is the **shorthand it
> parses out of that line** into `comment.marker`. One marker, two views: the full
> HTML comment in the body (carries `issue` + `spec` + `evidence`; `issue` is the
> linkify-safe match key), the `flow-evt:<event>` token the adapter exposes as
> `comment.marker`. **On read, normalize tracker mention-markup** (`<issue …>KEY</issue>` →
> `KEY`) before parsing the line, so a linkified marker still resolves. A comment whose `marker` is
> non-null is **flow's own** — skip it on pull.

**On pull:** a tracker comment whose `marker` is non-null (the `flow-next:sync`
marker is present) is **flow's own echo** → do **not** import it into the sync log
(it originated in flow). Only `marker == null` comments are genuine tracker-side.

**On post:** before posting a flow comment, `listComments` and check whether a
comment with the **same `issue` + `evt` + `evidence`** marker already exists → if so,
**skip the post** (already synced). This is the exact-match fence.

> **Linkify hazard (verified against live Linear, fn-52 smoke).** Linear (and
> GitHub) **auto-linkify any issue-key substring** (`WOR-17`, case-insensitive)
> that appears in body / comment markdown — **even inside an HTML comment** —
> rewriting it to mention markup like
> `<issue id="<uuid>" href="…/WOR-17">WOR-17</issue>`. So a marker carrying a
> tracker-first `spec=wor-17-slug` value comes back **mangled** (`spec=<issue …>WOR-17</issue>-slug`),
> and a literal `spec=` match fails. Mitigations, both applied:
> 1. **Write:** key the marker on `issue=<uuid>` (UUIDs are never linkified), not
>    on the tracker-key-bearing `spec` value.
> 2. **Read:** before matching ANY marker, normalize the comment body — strip the
>    tracker's mention markup back to bare text:
>    `s/<issue [^>]*>([^<]*)<\/issue>/$1/g` (GitHub uses `<a …>#123</a>`; strip the
>    same way). Then even an older `spec=`-keyed marker re-matches.
>
> The same hazard hits the flow back-reference: write it as a **`flow:<id>` label**
> (labels are plain text — never linkified), NOT as a body/title-embedded `[<id>]`
> reference when `<id>` carries a tracker key. The label is the safe primary; a
> `[<id>]` title prefix is linkify-prone and secondary at best.

### Layer 2 — the stored posted-comment id (durable)

When a flow comment is posted, its returned `comment.id` (the tracker UUID) is
recorded on the receipt / sync state. On the next run, a comment whose id is in the
posted-set is known-flow-originated even if its body were edited to strip the marker.
This survives a marker mangle (e.g. a tracker that rewrites HTML comments).

> flowctl persists the posted-comment ids it owns (the receipt records every post);
> the skill reads them back from `sync get-state` / the receipt log to seed the
> posted-set. (If the env's flowctl build doesn't yet expose a dedicated
> posted-id store, the marker + normalized hash layers below are sufficient on their
> own — the id layer is the durability belt-and-suspenders, not the sole fence.)

### Layer 3 — normalized-text hash (catches the human paste)

The hard case R8 names explicitly: **a human copy-pastes a flow comment** (e.g.
pastes the evidence block into a *new* tracker comment, or into the body) — it has
**no marker** and a **new id**, so Layers 1–2 miss it. Catch it with a
**normalized-text hash**:

1. **Normalize** the comment text: strip the marker line, lowercase, collapse runs
   of whitespace to a single space, trim, drop trailing punctuation-only lines.
   (Normalization is what avoids a *whitespace false-new* — a paste with different
   indentation/line-wrapping must hash identically to the original.)
2. **Hash** the normalized text (the same `_content_hash` flowctl uses for body
   echo-suppression — reuse it, don't invent a second hasher).
3. Maintain a **seen-set** of normalized hashes for every flow-posted comment.
   Before importing a marker-less tracker comment into the sync log, compute its
   normalized hash; **if it matches a flow-posted comment's hash → it's a paste of
   flow's own content → do NOT import** (and do not re-post).

This is the layer that makes "a human-pasted copy of a flow comment must not be
re-posted/re-imported" (R8) actually hold.

### Dedup decision flow

```
# PULL (tracker → flow sync log):
for c in listComments(trackerId):
  if c.marker != null:            continue   # Layer 1: flow's own marked comment — skip
  if c.id ∈ postedIds:            continue   # Layer 2: known flow-originated id — skip
  if normHash(c.body) ∈ seenSet:  continue   # Layer 3: human paste of flow content — skip
  append c to the spec's ## Sync Log         # a genuine tracker-side comment

# POST (flow → tracker):
marker = "<!-- flow-next:sync issue=<uuid> spec=<id> evt=<event> evidence=<sha|none> -->"
existing = listComments(trackerId)               # normalize each body first: strip <issue …>KEY</issue> → KEY
if any(e has marker with same issue+evt+evidence):  skip   # Layer 1 exact-match: already posted
else:
  body = marker + "\n\n" + <structured comment text>
  posted = postComment(trackerId, body)
  record posted.id in postedIds; record normHash(body) in seenSet
```

`lastSyncedAt` advances on a real comment reconcile (a genuine post or import); a
run that dedups everything to a no-op does **not** advance it (consistent with the
body echo-fence).

## The sync log on the flow side

Genuine tracker comments fold into a dedicated `## Sync Log` section of the spec —
append-only, newest at the bottom, each line crediting the tracker-side author and
timestamp (from the normalized `comment.author` / `createdAt`):

```markdown
## Sync Log
- 2026-06-03T10:12Z — **alice (Linear)**: Can we scope this to the EU region first?
- 2026-06-03T14:40Z — **bob (Linear)**: Confirmed with legal, proceed.
```

The sync log is **not** a flow requirement source — a tracker comment that reads
like a requirement is **logged as a comment, never promoted to an R-ID** (same
"bridge projects, never authors" rule as the body fold in
[body-merge.md](body-merge.md) Step 3). Promotion is a flow-authoring act
(interview/plan), not a sync act.

## Evidence comments (R8) — the flow → tracker payload

A `work.done` evidence comment renders the flow evidence (tests, PR) into a readable
tracker comment, marker-fenced:

```markdown
<!-- flow-next:sync issue=9b1e… spec=fn-42-add-oauth evt=work.done evidence=a1b2c3d -->

**fn-42.3 done** — Status/metadata who-wins implemented.

- Tests: `pytest tests/test_sync.py` (passed)
- Commit: `a1b2c3d`
- PR: #128
```

The `evidence=a1b2c3d` in the marker is the per-evidence dedup key: re-running
`work.done` for the same commit finds the existing marker (Layer 1) and **skips** —
no duplicate evidence comment.

## The async question-valve markers (fn-68 R15)

Backlog mode's `ask` stage posts a **question-valve comment** through this same
`postComment` channel, behind a **distinct marker family** that rides the Layer-1
dedup but is keyed on a stable `id` rather than `issue+evt+evidence`:

```html
<!-- flow-next:question id=<hash> status=open -->     <!-- the parked question -->
<!-- flow-next:answer   id=<hash> -->                 <!-- a human's reply, matched by id -->
```

- **`id` hashes STABLE fields only** — `subjectId` + blocked-stage + `reasonCode` +
  `questionSlug` (the question authoring lives in [steps.md](../steps.md) Phase 7).
  `subjectId` = the spec id when spec-backed, else the opaque tracker **UUID** —
  **never a bare tracker key** (`WOR-17` / `#123`), because the linkify hazard above
  mangles keys even inside HTML comments. The **free-prose reason is OUTSIDE the
  hash**, so rephrasing the question never spawns a duplicate anchor.
- **Dedup by `id` (Layer 1).** Before posting a question, `listComments` and check
  for an existing `flow-next:question id=<id>` → if present, **skip the re-post**
  (the subject is already parked). Same exact-match fence as the `flow-evt` marker,
  keyed on `id`.
- **`flow-next:question` is flow-posted ⇒ `marker` non-null ⇒ NOT pulled into the
  Sync Log** (Layer 1 on pull — it is flow's own structured comment, like every
  `flow-evt` comment). The question's durable home is the spec `## Open Questions`
  (spec-backed) or the tracker comment itself (tracker-only) — never the Sync Log.
- **`flow-next:answer` is the HUMAN's reply** — it is genuine tracker-side content,
  but it is NOT a free-form Sync-Log comment: the answer round-trip
  ([steps.md](../steps.md) Phase 7) matches it to its open question **by `id`**
  (threaded via `comment.parentId` on Linear, or flat by the body marker on
  GitHub) and imports it **under the matching `## Open Questions` entry**, flipping
  the question anchor to `status=answered`. An answer that matches no open question
  falls through to the normal Sync-Log append (a genuine tracker comment).

This is additive to the three-layer dedup — the question-valve markers are a second
marker *vocabulary* on the same Layer-1 channel, not a new dedup mechanism.

## The ONE edit-in-place exception — the rolling "flow-next status" comment (opt-in)

The **sole** edit-in-place surface, and only if opted in (`tracker.perEvent` policy
or a dedicated config flag). It is a single comment per issue, clearly marked, that
flow **updates in place** (not appends) to show the current spec status at a glance:

```html
<!-- flow-next:status issue=<uuid> spec=<id> rolling -->
**flow-next status** — in-progress · 2/4 tasks done · last sync 3h ago
```

- Identified by its **distinct** marker `flow-next:status … rolling` (NOT the
  `flow-next:sync` append marker) — so it is unmistakable and never collides with
  the append fence.
- On each sync, **find the rolling comment by its marker and update that one
  comment** (the one place `postComment`'s update path / a `save_comment(id, body)`
  is used to edit rather than create); if none exists, create it once.
- It reflects **only** derived status (the [status-sync.md](status-sync.md)
  normalized status + a task tally) — never user content, never evidence prose.

**Hard boundary:** this rolling comment is the **only** edit-in-place surface. It
does **NOT** apply to evidence, lifecycle, or user comments — those stay strictly
append-only. **If the rolling comment adds complexity, drop it and append a status
comment instead** — the append-only contract for every other comment must not be
weakened to accommodate it. It is opt-in and droppable; the append-only fence is not.

## Worked fixtures (runnable without a live tracker)

Each fixture is an input comment set + the expected dedup/append outcome — the
oracles for R8, exercisable by the host agent reading them (no live Linear; the live
`postComment`/`listComments` is the smoke phase).

### Fixture C-A — re-sync posts no duplicate (R8 headline)

**Setup:** `work.done` already posted an evidence comment for commit `a1b2c3d`
(marker `evt=work.done evidence=a1b2c3d` present on the issue).

**Action:** re-run the `work.done` sync for the same spec + same commit.

**Expected:** Layer 1 exact-match (`issue`+`evt`+`evidence`) finds the existing
marker → **skip the post**. No second comment.

**Oracle:** the issue still has exactly one `work.done evidence=a1b2c3d` comment;
the re-sync is a `noop` (no `postComment`). PASS iff no duplicate is posted.

### Fixture C-B — human-pasted flow comment is NOT re-imported (R8 headline)

**Setup:** flow posted an evidence comment (marker + body). A human then **copied
that body** (without the marker) into a *new* tracker comment, with different
indentation and line-wrapping.

**Action:** pull comments into the sync log.

**Expected:** the pasted comment has **no marker** (Layer 1 misses) and a **new id**
(Layer 2 misses), but its **normalized-text hash matches** the flow-posted comment
(Layer 3 hit) → **do NOT import** it into the sync log.

**Oracle:** the sync log gains **zero** entries from the paste; the normalized hash
matched despite the whitespace difference. PASS iff the paste is recognized as
flow's own content and skipped (this is the R8 anti-echo guarantee).

### Fixture C-C — genuine tracker comment IS imported (R8)

**Setup:** a PM posted a real question on the issue — no marker, unique text, new id.

**Action:** pull comments.

**Expected:** marker null (Layer 1 pass), id not in posted-set (Layer 2 pass),
normalized hash not in seen-set (Layer 3 pass) → **append to `## Sync Log`**,
crediting the PM + timestamp.

**Oracle:** exactly one new sync-log line with the PM's text and author; it is NOT
promoted to an R-ID. PASS iff the genuine comment is logged (and only logged).

### Fixture C-D — flow's own marked comment is skipped on pull (R8)

**Setup:** the issue has flow's `work.done` comment (marker present, so the adapter
set `comment.marker = "flow-evt:work.done"`).

**Action:** pull comments.

**Expected:** Layer 1 — `comment.marker != null` → **skip** (flow's own echo);
never re-import flow's structured comment into the sync log.

**Oracle:** the sync log gains nothing from flow's own comment. PASS iff the marked
comment is not echoed back into the spec.

### Fixture C-E — rolling status comment updates in place, append fence intact (R8)

**Setup:** the opt-in rolling `flow-next:status … rolling` comment exists; two prior
`work.done` append comments also exist.

**Action:** a status change triggers a rolling-comment refresh.

**Expected:** the **rolling** comment is **updated in place** (one comment, edited);
the two `work.done` append comments are **untouched** (append-only preserved). No new
append comment is created by the rolling refresh.

**Oracle:** the rolling comment's body changed, its id is unchanged, and exactly two
`work.done` append comments remain (neither edited, none added). PASS iff edit-in-
place is confined to the single rolling marker and the append fence holds for
everything else.

### Fixture C-F — question-valve is idempotent by `id` (fn-68 R15)

**Setup:** the `ask` stage posted a `flow-next:question id=H1 status=open` comment for
a blocked subject. A later tick re-triages the same subject (same `subjectId` +
blocked-stage + `reasonCode` + `questionSlug`) but **rephrases** the free-prose
reason.

**Action:** the `question` op recomputes `id` and `listComments` before posting.

**Expected:** the rephrase leaves `id == H1` (prose is OUTSIDE the hash) → Layer-1
dedup finds the existing `flow-next:question id=H1` → **skip the re-post**. No
duplicate question comment.

**Oracle:** exactly one `flow-next:question id=H1` comment; the re-triage is a
`noop`. PASS iff rephrasing never spawns a second anchor.

### Fixture C-G — answer round-trips by `id` on a FLAT tracker (fn-68 R15)

**Setup:** a `flow-next:question id=H2 status=open` comment exists on a **GitHub**
issue (flat — no threading). A human posts a reply comment carrying
`<!-- flow-next:answer id=H2 -->` plus the answer prose. GitHub gives it
`parentId: null`.

**Action:** pull/reconcile runs the answer round-trip.

**Expected:** despite `parentId == null`, the answer is matched to the open question
**by `id` (H2)** via the body marker. For a spec-backed subject it imports **under
the matching `## Open Questions` entry** and flips the anchor to `status=answered`;
for a tracker-only subject it stays in the tracker as the durable answered record.

**Oracle:** the question with `id=H2` is now `answered`, the answer prose is paired
with it (NOT merely appended to `## Sync Log`), and the flat `parentId` did not
prevent the match. PASS iff the flat-tracker answer round-trips exactly like a
threaded one.

## Boundaries

- **This is the comments/evidence layer, not the body merge, status, or transport.**
  The 3-way body merge is [body-merge.md](body-merge.md) (fn-52.4); status who-wins
  is [status-sync.md](status-sync.md); the `postComment`/`listComments` wire detail
  is [linear-ladder.md](linear-ladder.md) (fn-52.3) / the GitHub adapter (fn-52.7).
- **Append-only is the default and the contract** — the rolling status comment is the
  SOLE edit-in-place exception, opt-in and droppable; it never weakens append-only
  for evidence / lifecycle / user comments.
- **Dedup is three independent layers** — marker (exact), stored id (durable),
  normalized-text hash (catches the human paste). Any hit ⇒ skip.
- **The question-valve markers (fn-68 R15)** — `flow-next:question id=<hash>` /
  `flow-next:answer id=<hash>` — ride the Layer-1 channel keyed on a STABLE `id`
  (free prose outside the hash, never a bare tracker key). The authoring + answer
  round-trip live in [steps.md](../steps.md) Phase 7; this file owns their dedup +
  the `flow-next:answer`-vs-Sync-Log distinction.
- **Never promote a tracker comment to an R-ID** — log it; promotion is a flow-
  authoring act (interview/plan), not a sync act. The bridge projects.
- **State advances only on a real reconcile** — a run that dedups to a no-op does not
  advance `lastSyncedAt`.
- **Lifecycle wiring is fn-52.6** — this file defines the comment shape + dedup; the
  per-skill hooks that call it land there.
- **Codex mirror** (sync-codex.sh) is regenerated in fn-52.9 — keep this file
  Claude-native; no Codex-specific edits here.
