# Structured Review Findings

Review receipts may carry an optional `findings` object alongside their verdict
and original reviewer prose. The object is a portable, versioned projection of
the prose: consumers can render and compare findings without parsing Markdown,
while legacy receipts and unparseable responses remain valid.

This is a receipt contract, not an internal API. Consumers read stored receipts;
they do not call parser helpers or write resolution state back into Flow-Next.

The maximum-item local parser/validation benchmark uses the same strict
`<100 ms p95` ceiling over 30 warm runs. A representative parallel-suite run
observed 90.57 ms; that cost is operationally negligible within the end-to-end
workflow and supersedes the original 50 ms target. The benchmark permits no
model or network I/O.

## Version 1 schema

```json
{
  "findings": {
    "schemaVersion": 1,
    "sourceReceiptId": "review-…",
    "reviewKind": "implementation",
    "backend": "rp",
    "round": 2,
    "baseSha": "optional-reviewed-base",
    "headSha": "reviewed-head",
    "supersedesReceiptId": "optional-parent-generation",
    "items": [
      {
        "id": "finding-…",
        "priorFindingId": "optional-explicit-lineage-edge",
        "ordinal": 1,
        "severity": "P1",
        "confidence": 100,
        "classification": "introduced",
        "status": "fixed",
        "anchor": {
          "path": "src/example.py",
          "originalPath": "optional/base-side-name.py",
          "side": "head",
          "startLine": 42,
          "endLine": 45,
          "baseSha": "reviewed-base",
          "headSha": "reviewed-head",
          "blobOid": "optional-git-object-id"
        },
        "title": "Short finding title",
        "body": "Grounded explanation",
        "suggestion": "Optional remediation",
        "rIds": ["R3"],
        "firstSeenReceiptId": "review-…",
        "lastSeenReceiptId": "review-…"
      }
    ]
  }
}
```

Required container fields are `schemaVersion`, `sourceReceiptId`, `reviewKind`,
`backend`, `round`, `headSha`, and `items`. `baseSha` and
`supersedesReceiptId` are optional. Required item fields are `id`, `ordinal`,
`severity`, `confidence`, `classification`, `status`, `title`, `body`, `rIds`,
`firstSeenReceiptId`, and `lastSeenReceiptId`. `priorFindingId`, `anchor`, and
`suggestion` are optional. Unknown fields make a v1 container unsupported;
consumers must not reinterpret them as a compatible extension.

The receipt envelope binds the projection to its workflow:

| Receipt `type` | Required `findings.reviewKind` |
|---|---|
| `plan_review` | `plan` |
| `impl_review` | `implementation` |
| `completion_review` | `completion` |
| `qa_verdict` | `qa` |

The receipt `mode` must exactly equal `findings.backend`. A type/kind or
mode/backend mismatch invalidates the structured projection, so consumers fall
back to the receipt and original prose.

## Canonical values

| Field | Canonical values | Parser aliases |
|---|---|---|
| `reviewKind` | `plan`, `implementation`, `completion`, `qa` | none |
| `severity` | `P0`, `P1`, `P2`, `P3` | `Critical` → `P0`; `Major` → `P1`; `Minor` → `P2`; `Nitpick` → `P3` |
| `confidence` | `0`, `25`, `50`, `75`, `100` | none |
| `classification` | `introduced`, `pre_existing` | `pre-existing` / `pre existing` → `pre_existing` |
| `status` | `open`, `fixed`, `not_fixed`, `withdrawn` | `fixed in review` / `resolved` → `fixed`; `not fixed` / `remains open` / `unresolved` → `not_fixed` |
| `anchor.side` | `base`, `head` | none |

Aliases describe deterministic ingestion of reviewer prose. Stored containers
always use canonical values. An unknown enum value invalidates the structured
container; it is never coerced to the nearest known value.

Canonical item order is severity `P0` through `P3`, confidence descending, then
ordinal ascending. Consumers preserve that order.

## Identity and lineage

`sourceReceiptId` identifies one findings generation. Whenever a finding is
first seen, its ID is exactly `finding-` plus the first 32 lowercase hexadecimal
characters of SHA-256 over the UTF-8 bytes
`flow-next-finding-v1\0<firstSeenReceiptId>\0<ordinal>` (the `\0` separators
are single NUL bytes). Every valid successor carries the complete prior
snapshot forward: each carried item keeps its ID and `firstSeenReceiptId`, while
`lastSeenReceiptId` advances. A `Prior finding N` ratchet record updates the
carried item's status; it is not required for carry-forward. Fully restated
finding prose is not semantic identity: without an explicit lineage edge, it
creates an additional finding and ID even when its content or ordinal resembles
an older item.

`priorFindingId` is an explicit edge used only when a parser cannot preserve an
older ID byte-for-byte. The new item keeps its new ID and names the older item;
the edge does not authorize replacing or deleting the prior generation. Only
stored `id` and `priorFindingId` fields establish identity—consumers never
match findings by title, body, anchor, ordinal, or other semantic similarity.
Every non-root generation is a complete snapshot of the lineage:
omitting a previously known finding makes the chain invalid rather than
silently resolving it.

### The prior-finding reply grammar

The ratchet prompt states one machine-read line per prior finding, at the start
of a line, echoing the ordinal the finding was rendered with:

```
Prior finding #1: fixed
Prior finding #2: not-fixed
Prior finding #3: withdrawn
```

Accepted statuses are `fixed`, `not-fixed`, and `withdrawn` (with the usual
aliases — `resolved`, `not fixed`, `not_fixed`, `remains open`, `unresolved`,
`fixed in review`). Nothing else parses. With exactly one prior finding the
ordinal may be omitted (`Prior finding: fixed`).

When every prior finding is fixed, one **aggregate all-clear** record may replace
the per-finding lines:

```
Prior findings: all fixed
```

The aggregate must consume its whole line — a qualified variant
(`… all fixed except finding #2`) is recognized-but-invalid rather than a sweep,
because sweeping there would mark the very finding the reviewer excluded as
fixed. Any per-finding record present **disables** the aggregate entirely
(explicit beats implicit, enforced by parse order). It never fires on an empty
prior set, and it never touches a `withdrawn` item.

**`unaddressed: []` in the closing JSON tail is NOT a prior-findings signal.**
That key answers which spec R-IDs the review left uncovered; it is emitted by
every review, including round 1 where no prior findings exist, and a prior
finding is not an R-ID. Treating it as an all-clear would mark real open findings
resolved, which is why the aggregate record is a dedicated line-family record
instead.

**An unrepeated `not_fixed` does not survive the round.** A carried item at
`not_fixed` reverts to `open` before the round's own records apply, so a
`not-fixed` stated once and then not restated cannot look like a repeat.
`fixed` and `withdrawn` are preserved — they are resolved terminals. This is what
makes the surviving stall rule (`same-not-fixed-lineage`) a statement about two
consecutive rounds rather than an echo of one.

Prose resolutions are invisible to the parser: a reviewer that answers the
ratchet in prose only leaves every prior carried forward, and the loop is then
bounded by the round cap alone.

Repeated writes preserve the former latest receipt in the latest pointer's
sibling history directory:

```text
<receipt-path>
<receipt-path>.history/<sha256(sourceReceiptId)>.json
```

The latest pointer location is selected by the calling workflow; committed
review receipts conventionally live under `.flow/review-receipts/`, while
bounded interactive runs may use caller-provided or temporary paths. Consumers
start from receipt paths handed over as evidence. They must not scrape
Flow-Next implementation files or assume that every receipt is committed.

## Anchors

An anchor is present only when the reviewer supplied a safe repository-relative
path and a positive line or line range. Absent location evidence produces no
anchor. A valid primary location without enough snapshot binding omits the
entire anchor candidate before supplemental `originalPath` or `blobOid`
metadata or range ordering is interpreted. Thus an inverted range on an
unbound anchor candidate is omitted with that candidate. Flow-Next never
guesses the missing binding. Malformed or conflicting primary locations,
unsafe primary paths, and invalid sides reject the entire structured
generation. Once the primary location is snapshot-bound, an inverted range
(`endLine < startLine`) rejects the structured generation. Once the primary
location is snapshot-bound, invalid supplemental paths or blob OIDs also reject
the generation. Consumers then fall back to the receipt and prose; they must
not repair or truncate invalid anchor evidence.

`side` says which reviewed snapshot owns the line range. `baseSha` and
`headSha` bind it to the compared snapshots. `originalPath` records the
base-side name for a rename, while `path` is the anchored name.
`blobOid`, when present, binds the location to a Git object. If a finding is
carried to a new review snapshot without fresh location evidence, the finding
remains but its old anchor is removed.

Consumers may use an anchor for navigation only after confirming its snapshot
binding. Absence of an anchor is not absence of a finding.

## Selecting the current generation

Currentness is a read-only projection, not a mutable flag:

1. Validate each candidate container and, when filters are known, keep only the
   requested `reviewKind` and `backend`.
2. Index unique `sourceReceiptId` values. Reject duplicate identities.
3. Validate every `supersedesReceiptId`: its parent must exist in the same
   review-kind/backend lineage and its `round` must be exactly one lower.
4. Find unsuperseded tips whose `headSha` equals the current review head.
   Exactly one must remain.
5. Walk that tip's ancestor chain and reject cycles, incomplete snapshots,
   duplicate replacement ownership, or finding identities whose first-seen
   record is absent.

Only the selected chain receives the step 5 finding-lineage checks; a
semantically incomplete stale sibling does not invalidate it. That tip's item
status is current. A supported receipt bound to another
`headSha` is stale evidence: retain and label it, but do not use it as current
resolution, approval, or ship state. A stale sibling tip does not invalidate
the one head-matching tip. Zero or multiple head-matching tips means “no
unambiguous current structured findings,” never “no findings.”

Receipt verdict remains the workflow gate. The `findings` projection explains
the finding stream; it does not independently grant `SHIP`.

## Bounds

| Surface | Limit |
|---|---:|
| Reviewer source input | 1 MiB UTF-8 |
| Encoded `findings` container | 256 KiB UTF-8 |
| Items per container | 200 |
| `rIds` per item | 32, unique |
| IDs, backend, and review-kind strings | 160 characters |
| `baseSha` and `headSha` | 160 characters |
| Anchor paths | 1,024 characters |
| Item title | 240 characters |
| Item body | 4,000 characters |
| Item suggestion | 4,000 characters |

R-IDs must use `R<digits>`. IDs and ordinals must be unique. `round` and
`ordinal` are positive JSON integers—booleans do not qualify—and a root
generation without `supersedesReceiptId` must use round 1. Anchor paths must be
normalized repository-relative paths without `..` traversal. Ranges use
positive integer lines. On a snapshot-bound anchor, `endLine` must be greater
than or equal to `startLine`; an unbound anchor candidate is omitted before
that ordering validation. `blobOid`, when present, is
7–64 lowercase hexadecimal characters.

Limits are rejection boundaries, not truncation targets. Oversize input,
overflowing output, duplicates, unsafe paths, invalid lineage, unknown enums,
or unsupported schema versions produce no usable structured container.

**Nothing shortens a prompt to fit a transport (fn-169).** Earlier releases sized
the rendered prior-finding block to `cursor-agent`'s argv cap and stopped emitting
items once the budget ran out. A reviewer shown a SUBSET of its own prior findings
can truthfully answer `Prior findings: all fixed` for everything it saw, and
sweeping the untruncated container then marked omitted, unverified findings
`fixed` — a false SHIP. The interim guard that withheld the aggregate sweep on
truncating backends is gone with the truncation itself: every backend now renders
every prior item, so the aggregate is sound by construction on all of them. The
bounds above remain *rejection* boundaries, which is a different thing entirely.

A resumed re-review carries no rendered items at all — the reviewer holds them in
its own session and answers the same per-ordinal grammar from memory of its own
findings, verified against the current code on disk. Prior findings are the one
payload with no identity to pass instead: they live in the receipt, not the tree,
so there is nothing for a reviewer to fetch. That is why the renderer still exists
and why the injected fallback keeps using it.

## Fallback behavior

The `findings` field is additive and optional:

- No field: use the receipt verdict and original prose.
- Supported, valid, current v1 field: structured rendering is allowed.
- Valid but stale field: show it as stale evidence; never as current state.
- Unsupported version, invalid field, or ambiguous lineage: ignore the
  structured projection and retain the receipt plus prose.
- Explicit empty `items`: means the parser recognized a no-findings `SHIP`
  response for that generation. It is not equivalent to a missing or rejected
  container.

Fallback must be labeled when a consumer presents a structured view. Never
merge fields from a stale/invalid container with prose or another generation
to manufacture one apparently current record.

## Global-criteria compliance (`criteria`)

Completion-review receipts (`type: completion_review` only) may carry a second
additive field beside `findings`: per-criterion compliance with the project's
standing global criteria in `.flow/criteria.md` (see
[`spec-template.md`](spec-template.md) § Global criteria):

```json
"criteria": [
  {"id": "G1", "status": "met"},
  {"id": "G3", "status": "violated", "note": "route added without contract regen"},
  {"id": "G4", "status": "n/a"}
]
```

- `id` is a G-ID (`G<digits>`, unique within the array); `status` is exactly
  one of `met` / `violated` / `n/a`; `note` is an optional one-liner (<=400
  chars).
- The field is projected deterministically from the reviewer's
  `## Global criteria` output section by `parse_review_criteria()` - same
  public boundary as the findings parser: unparseable, duplicate-id, or
  oversized content **degrades to absent, never an error**. Legacy receipts
  without the field stay valid.
- The `criteria` array is **authoritative for compliance status**; findings
  carry the detail (every `violated` criterion is also reported as a normal
  finding at reviewer-judged severity). No cross-validation links the two -
  a consumer renders compliance from `criteria` and detail from `findings`
  independently.
- When `.flow/criteria.md` is absent, the review prompt contains no criteria
  content and receipts carry no `criteria` field - absence is a silent no-op.

## Execution provenance (which model ran a stage)

Routing is expressed as intent in prose, so it is best-effort by nature. The
receipt surfaces therefore record which model *actually executed* a stage,
wherever the harness exposes that fact — recording only: nothing prescribes a
model, and nothing fails because a stage went unrecorded.

Three places carry it, all optional and all additive:

| Surface | Field | Written when |
|---|---|---|
| Review receipt | `model` (with `effort`) | The dispatcher resolved the model it ran |
| Review attempt row (`review_attempts[]`) | `model`, `effort` | The same dispatch resolved them; the rp/host path records neither, because a narrating agent's claim is not an observation |
| Stage-outcome line | trailing `(model: <what ran>)` | The harness exposed what ran that stage. Emitted by the two stage-line grammar sites (the work skill's final summary, a pilot tick's evidence echo) when the orchestrator knows what executed; omitted otherwise, and a corpus written before those emitters simply tallies `unknown` |

One rule governs all three: **an absent value means unknown, never the
configured or preferred model.** A preference is not an observation, so a
selector placeholder (`auto`, `default`, a literal `unknown`) records no value
at all — a ladder floor and an unrouted stage are both honestly unknown.

`flowctl usage --stages <spec-id>` aggregates the result: every counted stage
gets a `models` tally (stage-line observations) and a separate `receipt_models`
tally (receipt observations), keys being the observed models plus `unknown`.
The two stay separate for the same reason `ran` and `receipts` do — a receipt
is the same review a prose line may already describe, and merging them would
make a fully receipt-observed review read as half unknown. Together they are
the after-the-fact check on prose routing.

Consumers read this provenance for reporting only. It is optional metadata on
records that already existed; no consumer may branch on it, require it, or
treat its absence as a failure — a receipt without a `model` is exactly as
valid as one carrying it.

## Memory relationship

Receipts and memory serve different lifetimes. A receipt records what one
review generation found. Bug memory records a reusable lesson after a
non-trivial `NEEDS_WORK` → `SHIP` fix cycle. Work may synthesize a bug-memory
entry from the finding and the applied fix, but the memory entry is not a
finding status, does not supersede a receipt, and cannot make stale evidence
current.

Consumers should therefore:

- use receipt lineage for review currentness;
- use memory as explanatory context and recurrence prevention;
- preserve both records when they exist; and
- never write receipt resolution state from a memory audit or memory status.

## Consumer checklist

- Treat receipts as the stable handover; do not depend on parser functions or
  skill internals.
- Preserve the original receipt and reviewer prose.
- Validate the whole container before using any item.
- Match the current review head and require one unambiguous lineage tip.
- Preserve canonical order, IDs, statuses, R-IDs, and anchor snapshot binding.
- Label stale and fallback states explicitly.
- Ignore unsupported structured data without turning it into a pass.
- flowctl's convergence detector and ratchet read `findings.items` from a
  validated current container; they treat absent, malformed, stale, or
  truncated containers as inert rather than inferring convergence from prose.

## See also

- [`architecture.md`](architecture.md) — receipt and history locations.
- [`memory-schema.md`](memory-schema.md) — durable learning lifecycle.
- [`spec-template.md`](spec-template.md) — confidence and classification rules.
- [`../../../GLOSSARY.md`](https://github.com/gmickel/flow-next/blob/main/GLOSSARY.md) — canonical Receipt and
  Structured finding terms.
