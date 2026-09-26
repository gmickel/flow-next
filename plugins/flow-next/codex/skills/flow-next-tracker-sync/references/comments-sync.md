# Comments / evidence reconciliation — two-way append + dedup (R8)

The comments-sync reconcile body behind the [../steps.md](../steps.md) `push` /
`pull` / `reconcile` hooks (`postComment` / `listComments`). It syncs **comments and
evidence two-way, append-only**: flow lifecycle events post structured comments to
the issue; tracker-side comments pull into the spec's sync log. Because both
directions are **appends, there is no merge conflict** (unlike the body) — the whole
problem is **dedup**: never post the same flow comment twice (the facade's marker
check), never re-import a human-pasted copy of a flow comment (the agent's pull
fold).

It operates ONLY on the normalized `comment` struct
([adapter-interface.md](adapter-interface.md)); the transport
([linear-ladder.md](linear-ladder.md)) is the firewall, this file is the comment
shape + pull fold policy.

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
> else here — the marker format, the pull fold rules, the lifecycle-event → comment
> mapping — is a complete, runnable procedure with
> worked fixtures and explicit oracles below, exercisable without a live tracker.

## Two directions, both append-only

| Direction | What flows | Mechanism |
|---|---|---|
| **flow → tracker** | a structured comment per opted-in lifecycle event (work done + evidence, make-pr URL, completion-review verdict, …) | the facade `comment` op (or push `comment-file`); the facade adds the marker and posts |
| **tracker → flow** | genuine tracker-side comments (a PM's question, a reviewer's note) | the fetched comment listing → fold into the spec's `## Sync Log` |

Neither direction overwrites the other; both are appends. The skill posts/pulls only
for the events opted in via `tracker.perEvent.<event>` set to `comment` (or an event
whose policy implies a comment, e.g. `work.done` → status comment + evidence). With
every `perEvent` leaf defaulting to `off`, **nothing is posted until a user opts in**
(spec Boundaries).

Comment wording follows the artifact prose contract in [docs/prose.md](../../../docs/flow-next/prose.md) under its "structural contracts win" precedence — the marker, envelope, and projection-only constraints in this file stay authoritative; proceed without the doc when it is absent.

### Which lifecycle events post a comment (R8 / R10)

The R10 lifecycle touchpoints (wired into the 7 lifecycle skills) that produce a
**comment** here:

| Event (`tracker.perEvent` key) | Comment posted to the issue |
|---|---|
| `work.done` | a status comment + **evidence** (tests run, PR link if present) |
| `makePr` | **link** the PR to the issue (not just a comment) so it renders as a reviewable diff: make-pr create-and-finalize adds a non-closing `Ref <identifier>` to the PR body, then passes the explicit PR URL to the reconcile facade. Flowctl projects GitHub's native `Refs #N`, a deduplicated GitLab URL note, a Jira remote-link upsert with comment fallback, or Linear's rich `attachmentLinkURL` attachment. |
| `resolvePr` | an optional resolution-summary comment |
| `completionReview` | the completion-review verdict + R-ID coverage summary |

`work.firstClaim` typically drives a **status change** (→ in-progress, see
[status-sync.md](status-sync.md)), not a comment — but MAY also post a one-line
"work started" comment if the user set that event to `comment`. `capture` /
`interview` / `plan` primarily sync the **body** ([body-merge.md](body-merge.md));
they post a comment only when explicitly opted into `comment`.

The actual wiring (calling this reconcile from each skill's lifecycle hook) lives
in the lifecycle skills; this file defines the comment shape + dedup the wiring relies on.

## Dedup — the whole problem (R8)

Appends don't conflict, but a naive re-sync re-posts everything. The facade
deduplicates posts by marker. The pull fold is the agent's: it skips flow's own
marked comments (the marker check) and human-pasted copies of them (the human-paste fold
rule); **any** hit ⇒ skip the import.

### Marker check — the embedded marker (primary, exact)

Every flow-posted comment carries a **hidden HTML-comment marker** as its first
line. The marker is the canonical dedup key and the back-reference all at once:

```html
<!-- flow-next:sync issue=<issue-uuid> spec=<spec-id> evt=<event> evidence=<stable-token> -->
```

- `issue=<issue-uuid>` — the tracker issue's stable UUID. **Primary, linkify-safe
  dedup key** (a UUID is not an issue-key pattern, so trackers never rewrite it —
  see "Linkify hazard" below). The facade matches on `issue` + `spec` + `evt` +
  `evidence`.
- `spec=<spec-id>` — the flow spec this comment belongs to (e.g. `fn-42-add-oauth`
  or `wor-17-slug`). **For readability + the back-reference only — never the sole
  match key.** A tracker-first id (`wor-17-slug`) embeds the tracker key, which the
  tracker auto-linkifies (next note), mangling a literal `spec=` match.
- `evt=<event>` — the lifecycle event (`work.done`, `makePr`,
  `completionReview`, …).
- `evidence=<stable-token>` — the caller-owned occurrence identity: a
  task/evidence commit, reviewed or tested head, spec-content fingerprint, or
  merge commit. Every synthesized lifecycle comment input starts with this
  whitespace-free token; missing, empty, or placeholder evidence is rejected
  before a provider call. This makes a *re-post of the same occurrence*
  detectable even if the surrounding prose changed without collapsing later
  occurrences of the same event.

**Retry rule.** A post whose response failed to parse may still have LANDED.
Retry by re-invoking the facade with the same `evidence=<token>`: every invocation
lists the comments and skips the post when the marker is already present.

> **Marker reconciliation.** The normalized wire comment
> ([adapter-interface.md](adapter-interface.md)) has no marker field: recognize a
> flow comment by the HTML-comment marker line in its `body`. The flow-owned set
> is **closed** — `flow-next:sync`, `flow-next:question`, and the rolling
> `flow-next:status`; detect the whole set, or a parked **question** is imported
> into the Sync Log. **On read, normalize tracker mention-markup**
> (`<issue …>KEY</issue>` → `KEY`) before parsing the line, so a linkified marker
> still resolves. The **one exception** is `flow-next:answer`: it is the human's
> reply (genuine content), not a flow comment; the answer round-trip claims it by
> `id` BEFORE the generic Sync-Log append.

**On pull:** a tracker comment carrying a flow-owned marker is **flow's own echo**
→ do **not** import it into the sync log (it originated in flow). Only marker-less
comments (and unmatched `flow-next:answer` replies) are genuine tracker-side.

**On post:** the facade lists the comments and skips the post when a comment with
the **same `issue` + `spec` + `evt` + `evidence`** marker already exists. This is
the exact-match fence.

> **Linkify hazard (verified against live Linear).** Linear (and
> GitHub) **auto-linkify any issue-key substring** (`WOR-17`, case-insensitive)
> that appears in body / comment markdown — **even inside an HTML comment** —
> rewriting it to mention markup like
> `<issue id="<uuid>" href="…/WOR-17">WOR-17</issue>`. So a marker carrying a
> tracker-first `spec=wor-17-slug` value comes back **mangled** (`spec=<issue …>WOR-17</issue>-slug`),
> and a literal `spec=` match fails. Mitigations, both applied:
> 1. **Write:** key the marker on `issue=<uuid>` (UUIDs are never linkified), not
> on the tracker-key-bearing `spec` value.
> 2. **Read:** before matching ANY marker, normalize the comment body — strip the
> tracker's mention markup back to bare text:
> `s/<issue [^>]*>([^<]*)<\/issue>/$1/g` (GitHub **and GitLab** auto-linkify `#N` /
> `<project>#N` to `<a …>#123</a>` anchor markup; strip it the same way). Then even an
> older `spec=`-keyed marker re-matches. (GitLab flow-first specs carry `fn-NN` in
> markers; tracker-first ones carry synthetic `gl-N-slug` — either way the strip is uniform.)
>
> The same hazard hits the flow back-reference: write it as a **`flow:<id>` label**
> (labels are plain text — never linkified), NOT as a body/title-embedded `[<id>]`
> reference when `<id>` carries a tracker key. The label is the safe primary; a
> `[<id>]` title prefix is linkify-prone and secondary at best.

### Human-paste fold rule (agent-side)

The hard case R8 names explicitly: **a human copy-pastes a flow comment** (e.g.
pastes the evidence block into a *new* tracker comment) — it has **no marker** and
a **new id**, so the marker check misses it. The facade receives an already-folded spec and
does not filter pasted copies, so the pull fold applies this rule over the fetched
listing:

1. **Normalize** each comment body: strip mention markup, strip the marker line,
   lowercase, collapse runs of whitespace to a single space, trim, drop trailing
   punctuation-only lines. (Normalization is what avoids a *whitespace false-new* —
   a paste with different indentation/line-wrapping must match the original.)
2. A marker-less comment whose normalized body equals the normalized body of a
   flow marker comment **in the same listing** is a paste of flow's own content →
   **do NOT import** it.

This is the rule that makes "a human-pasted copy of a flow comment must not be
re-imported" (R8) actually hold.

### Dedup decision flow

```
# PULL (tracker → flow sync log), over the fetched listing:
for c in listing:
  if c.body has a flow-owned marker: continue   # marker check: flow's own marked comment — skip
                                             #   (flow-next:sync / flow-next:question / flow-next:status)
  if c carries flow-next:answer id=<id>:     # human ANSWER (marker stays null): the round-trip
     claim it by <id> for the question-valve (steps.md Phase 7) BEFORE Sync-Log;
     if it MATCHED an open question:  continue   # imported under ## Open Questions, not the Sync Log
     # else (no matching open question) fall through — it is a genuine comment
  if norm(c.body) == norm(f.body) for any flow marker comment f in the listing:
                                  continue   # human paste of flow content — skip
  append c to the spec's ## Sync Log         # a genuine tracker-side comment
```

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
tracker comment. The caller's file starts with `evidence=a1b2c3d`; the facade turns
that line into the marker, so the posted comment reads:

```markdown
<!-- flow-next:sync issue=9b1e… spec=fn-42-add-oauth evt=work.done evidence=a1b2c3d -->

**fn-42.3 done** — Status/metadata who-wins implemented.

- Tests: `pytest tests/test_sync.py` (passed)
- Commit: `a1b2c3d`
- PR: #128
```

The `evidence=a1b2c3d` in the marker is the per-evidence dedup key: re-running
`work.done` for the same commit, the facade finds the existing marker and **skips** —
no duplicate evidence comment.

## The async question-valve markers

Backlog mode's `ask` stage posts a **question-valve comment** through this same
`postComment` channel, behind a **distinct marker family** that rides the marker
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
- **Round-aware dedup by `id` (marker check).** Before posting a question,
  `listComments` and collect matching `flow-next:question` and
  `flow-next:answer` markers. Compare normalized immutable `created_at` values:
  latest question → **skip** (the subject is parked); latest answer → post a new
  question round with the same stable id. A mixed history with missing, invalid,
  or tied timestamps fails closed. This prevents both duplicate open questions
  and the opposite bug where an old answer suppresses every future round.
- **Concurrent dedup.** Before `listComments`, flowctl takes a local claim keyed
  by provider, durable issue id, and stable question id, and holds it through
  any post. A racing identical ask returns retryable `question_in_flight`; its
  retry then sees and deduplicates against the winner's open marker.
- **`flow-next:question` is flow-posted ⇒ it carries a flow-owned marker ⇒ NOT
  pulled into the Sync Log** (the marker check on pull — it is flow's own structured
  comment, like every flow-marked comment). The
  question's durable home is the spec `## Open Questions` (spec-backed) or the tracker
  comment itself (tracker-only) — never the Sync Log.
- **`flow-next:answer` is the HUMAN's reply** — it is genuine tracker-side content,
  but it is NOT a free-form Sync-Log comment: the answer round-trip
  ([steps.md](../steps.md) Phase 7) matches it to its open question **by `id`**
  (threaded via `comment.parentId` on Linear, or flat by the body marker on
  GitHub, GitLab **and Jira** — GitLab issue notes and Jira issue comments are flat,
  `parentId: null`, matched by the `<!-- flow-next:answer id=… -->` body marker exactly
  like GitHub) and imports it
  **under the matching `## Open Questions` entry**, flipping
  the question anchor to `status=answered`. An answer that matches no open question
  falls through to the normal Sync-Log append (a genuine tracker comment).

This is additive to the marker dedup — the question-valve markers are a second
marker *vocabulary* on the same marker channel, not a new dedup mechanism.

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

### Fixture C-B — human-pasted flow comment is NOT re-imported (R8 headline)

**Setup:** flow posted an evidence comment (marker + body). A human then **copied
that body** (without the marker) into a *new* tracker comment, with different
indentation and line-wrapping. Both comments are in the fetched listing.

**Action:** pull comments into the sync log.

**Expected:** the pasted comment has **no marker** (the marker check misses), but its
normalized body **equals** the normalized body of the flow-marked comment in the
same listing (human-paste fold rule) → **do NOT import** it into the sync log.

**Oracle:** the sync log gains **zero** entries from the paste; the normalized
bodies matched despite the whitespace difference. PASS iff the paste is recognized as
flow's own content and skipped (this is the R8 anti-echo guarantee).

### Fixture C-C — genuine tracker comment IS imported (R8)

**Setup:** a PM posted a real question on the issue — no marker, unique text, new id.

**Action:** pull comments.

**Expected:** no marker (the marker check passes), normalized body matches no flow-marked
comment in the listing (human-paste rule pass) → **append to `## Sync Log`**,
crediting the PM + timestamp.

**Oracle:** exactly one new sync-log line with the PM's text and author; it is NOT
promoted to an R-ID. PASS iff the genuine comment is logged (and only logged).

### Fixture C-D — flow's own marked comment is skipped on pull (R8)

**Setup:** the issue has flow's `work.done` comment (its body carries the
`<!-- flow-next:sync … evt=work.done … -->` marker).

**Action:** pull comments.

**Expected:** marker check — the body carries a flow-owned marker → **skip** (flow's own echo);
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

### Fixture C-F — question-valve is idempotent by `id`

**Setup:** the `ask` stage posted a `flow-next:question id=H1 status=open` comment for
a blocked subject. A later tick re-triages the same subject (same `subjectId` +
blocked-stage + `reasonCode` + `questionSlug`) but **rephrases** the free-prose
reason.

**Action:** the `question` op recomputes `id` and `listComments` before posting.

**Expected:** the rephrase leaves `id == H1` (prose is OUTSIDE the hash) →
the marker check finds the latest marker is the existing
`flow-next:question id=H1` → **skip the re-post**. No duplicate open question.

If a later `flow-next:answer id=H1` exists, the next ask posts a new question
round with the same id. A subsequent retry sees that newer question and skips.

**Oracle:** exactly one `flow-next:question id=H1` comment; the re-triage is a
`noop`. PASS iff rephrasing never spawns a second anchor.

### Fixture C-G — answer round-trips by `id` on a FLAT tracker

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
  The 3-way body merge is [body-merge.md](body-merge.md); status who-wins
  is [status-sync.md](status-sync.md); the `postComment`/`listComments` wire detail
  is [linear-ladder.md](linear-ladder.md) / the GitHub adapter.
- **Append-only is the default and the contract** — the rolling status comment is the
  SOLE edit-in-place exception, opt-in and droppable; it never weakens append-only
  for evidence / lifecycle / user comments.
- **Dedup is split** — the facade's exact marker check on post; on pull, the
  agent skips flow-marked comments and marker-less comments whose normalized body
  matches a flow-marked comment in the same listing. Any hit ⇒ skip.
- **The question-valve markers** — `flow-next:question id=<hash>` /
  `flow-next:answer id=<hash>` — ride the marker channel keyed on a STABLE `id`
  (free prose outside the hash, never a bare tracker key). The authoring + answer
  round-trip live in [steps.md](../steps.md) Phase 7; this file owns their dedup +
  the `flow-next:answer`-vs-Sync-Log distinction.
- **Never promote a tracker comment to an R-ID** — log it; promotion is a flow-
  authoring act (interview/plan), not a sync act. The bridge projects.
- **Lifecycle wiring lives in the lifecycle skills** — this file defines the comment shape + dedup; the
  per-skill hooks that call it land there.
