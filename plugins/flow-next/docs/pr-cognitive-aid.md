# PR cognitive-aid consumer contract

`/flow-next:make-pr` can persist one bounded, versioned explanation of a change
and render it in GitHub Markdown. The existing host agent composes the intent;
`flowctl` validates, stores, selects, and renders the object without another
model or network call.

## Storage and identity

Each generation is an immutable JSON file:

```text
.flow/artifacts/<spec-id>/pr-cognitive-aid/<artifactId>.json
```

The path is part of the v1 contract. Enumerate that home; do not scrape PR
Markdown or import flow-next's internal Python functions. A generation binds
`artifactId`, `specId`, `baseSha`, `headSha`, and `generatedAt`.
`supersedesArtifactId` links a later generation to its predecessor.

The current object is the unique newest valid chain tip whose `baseSha` equals
the current merge base and whose `headSha` equals the PR head. A stale,
unsupported, invalid, forked, or ambiguous chain remains evidence but supplies
no current verification or ship claim. Select a labeled fallback; never merge
legacy fields into a partial v1 view.

Make-pr's resolve step reuses a valid current generation at the same base and
head, including one written from sparse input. A same-head successor that
explicitly supersedes the tip publishes a deliberate correction to authored
content. A moved head, missing artifact, or failed validation requires composing
again.

Aid generations and their `.write.lock` files are ignored by the managed
`.flow/.gitignore` block after `flowctl init` refreshes it. HTML lenses and
other artifact kinds remain trackable. Already tracked aid files require a
one-time maintainer untracking step; flowctl never removes them from the index.

Ignored aids are per-clone state. A PR created on another host or clone has no
stored walkthrough available to a projector reading this clone's artifact home.
The PR body still travels with the PR; the local aid files do not.

## Sparse authoring

Four optional authored fields are additive within `changeWalkthrough`.
The stored `schemaVersion` remains `1` and the artifact path above is unchanged.

| Field | Type | Meaning |
| --- | --- | --- |
| `userImpact` | string | What changes for a user or operator. |
| `blastRadius` | string | Who or what the change touches and why it is safe or risky. |
| `tradeoffs` | string | Rejected alternatives a reviewer would otherwise ask about. |
| `openItems` | string | Work that remains unfinished. |

Each field allows an empty string and up to 4,000 characters. Omit fields with
no authored content. Existing artifacts without them remain valid. Wrong types
are rejected with the field's path; unknown fields remain rejected.

Each `changeWalkthrough.proof[]` cell also accepts an additive optional
`outcome` string with exactly three values: `pass`, `fail`, or `unverified`.
A verification step nobody ran is a proof cell with outcome `unverified`;
its `value` explains the gap. Cells without an outcome remain valid, preserving
artifacts stored before this addition. Invalid outcomes are rejected with the
cell's path. All four input entry points below preserve the authored fields
and proof-cell outcomes during sparse expansion and storage.

Validate, write, render --file, and html-input --file accept rows with only
judgment fields. Missing `changeType`, `additions`, and `deletions` are filled
from the bound diff. An omitted `diffUrl` becomes
`/<owner>/<repo>/blob/<headSha>/<path>`, with the path URL-encoded and slashes
preserved. The repository identity comes from the local origin remote and the
SHA from the artifact's `headSha`. Without a resolvable identity or bound diff
metadata for the row, the optional field stays absent; it also stays absent for
a deleted path, which has no blob at the head, and if the derived URL exceeds
the v1 length bound. The path shape is the one the pull-request forge that
make-pr opens against serves; a reader on another forge should treat the link
as advisory. Readers receive either that literal
string shape or no `diffUrl` key. Supplied links retain
the existing URL-safety validation; they need not equal the derived link.
Explicit counts and change types must match the bound diff. Row references
inherit the corresponding group fields unless explicitly supplied.

Unlisted changed paths get rows with `summary: ""`, diff-only `sourceRefs`, and
empty `rIds`/`taskIds`. An empty summary means "not described", is legal on any
row, and carries no semantic grounding requirement. A non-empty summary keeps
the existing grounding rule. Every row still cites the bound `diff_metadata`
source and validates any supplied references. The stored form has no marker
that distinguishes an authored empty summary from a flowctl-added one.
These rows make no semantic claim. They are appended in
path order to existing step groups, filling the last step first and preceding
steps if its 200-file limit is reached. Group identity, authored row order,
and the one-to-seven step limit remain unchanged; no optional group is invented.
The persisted schema stays v1, with explicit fields on every row.

Only `.flow/tasks/*.json` and `.flow/specs/*.json` (direct children), known
package-manager lockfile names, and `plugins/flow-next/codex/` determine default
attention: state and lockfiles are `mechanical`, the mirror is `generated`.
Known lockfile names are `package-lock.json`, `npm-shrinkwrap.json`,
`pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, `bun.lockb`, `Cargo.lock`, `Gemfile.lock`,
`poetry.lock`, `uv.lock`, `Pipfile.lock`, and `composer.lock`, at any depth.
Other unlisted paths are `canonical`, including authored Flow Markdown and
arbitrary directories named `generated` or `dist`. An authored row without a
matching pattern must supply `attentionClass`; an explicit class always wins.

## Semantic projection

The envelope owns one bounded `sources[]` table. Every proof, group, and file
claim carries `sourceRefs`; every file-level R-ID or task link has a matching
same-record source. Preserve:

- artifact identity and base/head currentness;
- source IDs and their `kind`/`ref` bindings;
- group array order, ordinal, and kind;
- exact file membership in the owning group;
- separate `changeType` and `attentionClass` values;
- file-level `sourceRefs`, `rIds`, and `taskIds`;
- optional `kept` and `verify` groups as first-class semantics.

GitHub Markdown is the canonical hosted-review rendering. The optional HTML
render lens consumes the same exact validated v1 object when one is available
and uses it as the authoritative source for the fields above. HTML may enrich
navigation, collapse state, and bounded inline-diff display; it may not
reclassify files, reorder groups, invent badges, or blend stale and legacy
data. The lens embeds the lossless output of
`flowctl pr-cognitive-aid html-input --file <validated-object>` so consumers can
recover and compare the exact JSON object. It remains local-only and leaves
`HEAD` unchanged; committing that HTML to the reviewed branch would immediately
stale its own head-bound input. Raw diff text is not stored in the object.

Full validation rules, bounds, and fallback behavior are defined by the
[`pr-cognitive-aid` flowctl commands](flowctl.md#pr-cognitive-aid). The HTML
presentation boundary remains documented in
[`html-artifacts.md`](html-artifacts.md).

## Markdown briefing

Every pull-request size uses the same deterministic briefing. The artifact
supplies all content; rendering reads no live Flow state. Invalid artifacts
produce no briefing, so make-pr uses its existing fallback.

Sections appear in this order, and empty sections have neither a heading nor
a placeholder:

| Section | Artifact content |
| --- | --- |
| Why | `changeWalkthrough.thesis`, with the intent and approach. |
| What changes for a user or operator | `changeWalkthrough.userImpact`. |
| Scope | Grouped files and requirement coverage from the artifact. |
| Blast radius | `changeWalkthrough.blastRadius`. |
| Verification | `changeWalkthrough.proof[]`. |
| Tradeoffs | `changeWalkthrough.tradeoffs`. |
| Open items | `changeWalkthrough.openItems`. |

Scope uses one numbered, diff-fenced file tree per group. Each described file carries its
one-line purpose and requirement IDs. Remaining files collapse to a counted
line that distinguishes mechanical files from files not described; an empty
summary never implies safe-to-skim status. A group with no described files
shows its title and that count. One coverage line maps requirement IDs to the
numbers of the groups that evidence them and names uncovered requirements; a
requirement evidenced only by groups without files names those groups. A per-criterion
table appears only when a requirement is unevidenced or undeclared. Requirement
sources in `sources[]` supply the declared set, including requirements cited
by no group.

Verification renders only authored proof cells. Outcome `pass` receives a
checked box; `fail` and `unverified` receive unchecked boxes with their distinct
status and the cell's note. A cell without an outcome is a plain list item with no
checkbox. Old artifacts therefore keep their evidence without gaining a pass
claim. Proof cells with no outcome are still valid, and absent proof cells
omit the section entirely.

The renderer fits ordinary briefings within 40 lines, counting blank lines.
Before collapsing anything, it reflows a multiline thesis if needed, unless
that thesis plus its Why heading, two blank lines and identity comment already
exceeds 40 lines. That exceptional thesis remains in full; other content is
counted. Why and the coverage line never collapse.

Collapse stops as soon as the body fits: proof cells without outcomes first,
then pass cells, each from the end; described file rows from later groups
before earlier groups; then lines beyond the first in tradeoffs, blast radius,
user/operator change and finally open items. Each field keeps its first line
and a counted remainder; one-line fields survive ordinary collapse. Fail and
unverified cells collapse only after these steps. Proof counts distinguish
each outcome. Exhausted scope and optional coverage-table detail use counted
summaries when needed. Counted lines and coverage have a preceding blank line.
Apostrophes and quotation marks render literally; markup-injection characters
remain neutralized.

Artifact ID, base SHA and head SHA appear together in one invisible HTML
comment. File statistics, repeated provenance, review plans and generated-by
footers stay out of the visible briefing. The complete stored artifact remains
available to the HTML lens and other consumers; neither its lossless
`html-input` output nor the lens changes with the markdown briefing.

## Canonical fixture and downstream vendoring

Flow-Next owns the maximum-normal v1 fixture and its metadata:

- [`golden.json`](../tests/fixtures/pr-cognitive-aid/v1/golden.json)
- [`golden.meta.json`](../tests/fixtures/pr-cognitive-aid/v1/golden.meta.json)

Metadata records `schemaVersion`, the upstream `sourcePath`, the full
`sourceCommit`, the immutable Git `sourceBlob`, the SHA-256 of the exact
`golden.json` bytes, and the executable performance contract. The blob and
SHA-256 are over the file bytes as checked in - not parsed/reformatted JSON.
Consumers use those byte identities as the durable provenance seam:
`sourceCommit` remains an audit breadcrumb and may be absent from a shallow
checkout or become unreachable after a squash merge, while the blob remains
reachable from every tree containing the fixture.

The maximum-normal fixture's validation plus GitHub Markdown rendering must
complete within a strict `<100 ms p95` over 30 warm runs, excluding atomic disk
write and permitting no model or network I/O. This ceiling supersedes the
original 50 ms target: a representative parallel-suite run observed 90.57 ms,
which is operationally negligible within the end-to-end workflow. Consumers
should treat `performanceBudget.p95MillisecondsExclusive` as an exclusive
upper bound, not round or reinterpret it as `<=`.

`performanceBudget.clock` names the clock the budget is measured on:
`time.process_time`, process CPU time. Wall clock is wrong for this budget -
the operation is pure in-memory work, so under a parallel test suite a
wall-clock p95 measures scheduler contention between sibling interpreters
rather than the operation itself. Consumers should measure on their runtime's
equivalent process-CPU clock, not on wall time.

Flow Swarm vendors byte-identical copies of both files under its own test
fixtures. Its CI:

1. hashes the local vendored `golden.json`;
2. compares that hash with the vendored metadata's pinned upstream `sha256`;
3. validates and renders locally against the vendored bytes.

No Flow-Next checkout, private repository access, or cross-repository network
request is required in downstream CI. A consumer may verify a prepared update
before vendoring with:

```bash
shasum -a 256 plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.json
```

Changing the schema requires a new versioned fixture directory. Changing only
the v1 fixture requires copying the new bytes and metadata together and
updating the pinned digest in the same downstream change. Never regenerate or
pretty-print the fixture independently in the consumer.

## Information-architecture references

These high-resolution images are normative hierarchy and interaction
references, not pixel-copy requirements:

- [Overview, thesis, proof metrics, and logical sequence](../../../.flow/assets/pr-aid/change-walkthrough-overview.jpeg)
- [Progressive disclosure from step to file to diff](../../../.flow/assets/pr-aid/change-walkthrough-expanded-diff.jpeg)
- [Grouped files, deliberate non-changes, and verification](../../../.flow/assets/pr-aid/change-walkthrough-grouped-files.jpeg)

Flow-Next approximates that hierarchy in GitHub Markdown. Richer consumers can
add interaction while preserving the semantic projection above.
