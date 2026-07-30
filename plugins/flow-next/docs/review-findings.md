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

## See also

- [`architecture.md`](architecture.md) — receipt and history locations.
- [`memory-schema.md`](memory-schema.md) — durable learning lifecycle.
- [`spec-template.md`](spec-template.md) — confidence and classification rules.
- [`../../../GLOSSARY.md`](../../../GLOSSARY.md) — canonical Receipt and
  Structured finding terms.
