# PR cognitive-aid consumer contract

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


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
`.flow/.gitignore` block after `flowctl init` refreshes it. Other artifact
kinds remain trackable. Already tracked aid files require a
one-time maintainer untracking step; flowctl never removes them from the index.

Ignored aids are per-clone state. A PR created on another host or clone has no
stored walkthrough available to a projector reading this clone's artifact home.
The PR body still travels with the PR; the local aid files do not.

## Several specs in one PR

Optional `specIds` lists 1–32 canonical spec IDs without duplicates and includes
`specId`, which still binds the expected host and storage path. Schema version
stays 1. With several IDs, spec sources may name any member and task sources
may name tasks of any member. Every `rid` source ref and `rIds` entry must use
`fn-12:R4`: short spec ID, colon, bare requirement ID. The short ID must resolve
to exactly one listed spec. Bare IDs are invalid in this mode. Without `specIds`,
or with one member, existing validation and rendering remain unchanged and
qualified IDs are invalid. Sparse expansion preserves `specIds`.

Row tags and per-criterion tables retain qualified IDs. Coverage has one line
per spec in `specIds` order, for example `Coverage fn-12: R1 → group 1; R2 → groups 1, 2`.
Specs without declared requirements have no coverage line; declared but
uncovered requirements remain visible.

Membership requires a spec newly done at HEAD and at least one of its task files changed in the range; the host is always included, while record-only sibling closes are excluded. Siblings whose recorded branch has a done spec at its merge base with HEAD are also excluded, including true merge commits; squash landings, deleted branches, and absent branch names remain eligible.
The undeclared-requirements abort applies only to the host; sibling requirements remain visible as uncovered.
Under several specs, requirement ids render qualified (`fn-12:R1`).
Land selects specs by branch name. With no match, it reads recursive git trees at the head and the base: newly done specs qualify only with a task entry new or changed against base. Truncated reads need human attention. Land repairs the pull request it is given; merging requires session merge authorization. A null push date falls back to the head's earliest check-suite creation time, then committer date.
Two listed specs sharing a number within the same ID prefix cannot be qualified unambiguously.

## Sparse authoring

Five optional authored fields are additive within `changeWalkthrough`.
The stored `schemaVersion` remains `1` and the artifact path above is unchanged.

| Field | Type | Meaning |
| --- | --- | --- |
| `userImpact` | string | What changes for a user or operator. |
| `blastRadius` | string | The review focus: where to start reading, one to three places to look hard and why, and the feedback wanted. |
| `tradeoffs` | string | Rejected alternatives a reviewer would otherwise ask about. |
| `openItems` | string | Work that remains unfinished and no proof cell names. |
| `shape` | string | One fenced code block (`diff` or `text`) of the new or changed public surface, or a call tree. |

Each field allows an empty string and up to 4,000 characters. Omit fields with
no authored content. A nonblank `shape` must open and close with a code fence. Existing artifacts without them remain valid. Wrong types
are rejected with the field's path; unknown fields remain rejected.

Each `changeWalkthrough.proof[]` cell also accepts an additive optional
`outcome` string with exactly three values: `pass`, `fail`, or `unverified`.
A verification step nobody ran is a proof cell with outcome `unverified`;
its `value` explains the gap. Cells without an outcome remain valid, preserving
artifacts stored before this addition. Invalid outcomes are rejected with the
cell's path. All three input entry points below preserve the authored fields
and proof-cell outcomes during sparse expansion and storage.

Validate, write, and render --file accept rows with only
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
source and validates any supplied references. Appended rows carry `restOfDiff: true`
so Markdown attributes them to the whole diff; existing complete artifacts without
the tag retain their grouping.
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

GitHub Markdown is the canonical hosted-review rendering. Any other consumer
reads the same validated v1 object and treats it as the authoritative source
for the fields above: it may enrich navigation, but it may not reclassify
files, reorder groups, invent badges, or blend stale and legacy data. Raw diff
text is not stored in the object.

Full validation rules, bounds, and fallback behavior are defined by the
[`pr-cognitive-aid` flowctl commands](flowctl.md#pr-cognitive-aid).

## Markdown briefing

Every pull-request size uses the same deterministic briefing. The artifact
supplies all content; rendering reads no live Flow state. Invalid artifacts
produce no briefing, so make-pr uses its existing fallback.

The briefing leads with what a reviewer needs before opening the diff and does
not repeat what the forge already shows (the changed-file list, line totals).
Sections appear in this order, and empty sections have neither a heading nor
a placeholder:

| Section | Artifact content |
| --- | --- |
| Why | `changeWalkthrough.thesis`, with the intent and approach. |
| Review focus | `changeWalkthrough.blastRadius`. |
| Needs you | Proof cells with outcome `fail` or `unverified`, then each line of `openItems` as `- Open: …`. |
| Shape | `changeWalkthrough.shape`, verbatim. |
| What changes for a user or operator | `changeWalkthrough.userImpact`. |
| Reading order | The groups, in review order. |
| Tradeoffs | `changeWalkthrough.tradeoffs`. |
| Verified | The remaining proof cells. |

Reading order gives every group a numbered bold title, its requirement ids once
(`[R1, R2]`, qualified under several specs), and its trimmed, neutralized summary,
including fileless problem, principle, kept and verify groups. A group with a
described canonical row ends with `Start at` and that row's code-span path, linked
through `diffUrl` when available; the first described row in author order is the
start file, and row summaries stay in the artifact. Groups whose files are all
undescribed collapse into one closing `Safe to skim:` line, which also names the
remaining mechanical and generated files: by path when there are at most five,
otherwise as counts with their group numbers. `Uncovered: R7` names declared
requirements that no group or row cites; nothing is printed when all are covered
or none are declared. Sparse expansion's appended rows stay in the artifact; the
body names them only when they are mechanical or generated. Spec and task markdown
under `.flow/` is canonical unless explicitly classed mechanical. Whitespace-only
summaries are rejected with the field name; empty file summaries remain legal.

Outcome `pass` receives a checked box; `fail` and `unverified` receive unchecked
boxes with their distinct status and the cell's note. A cell without an outcome
is a plain list item with no checkbox, so old artifacts keep their evidence
without gaining a pass claim. Absent proof cells omit Verified.

The renderer makes one deterministic pass with no body line budget. Why and the
authored fields keep their line breaks. Apostrophes and quotation marks render
literally; markup-injection characters remain neutralized, including mentions
(`@name`), which would ping a user. Issue and pull-request numbers (`#123`), URLs
and bare commit SHAs stay live links, so `fixes #1` in authored prose closes that
issue on merge, as it would in a hand-written body. Shape is the one field that
renders as authored, inside its own code fence.

Artifact ID, base SHA and head SHA appear together in one invisible HTML
comment. File statistics, repeated provenance, review plans and generated-by
footers stay out of the visible briefing. The complete stored artifact remains
available to other consumers and does not change with the markdown briefing.

## Canonical fixture and downstream vendoring

Flow-Next owns the maximum-normal v1 fixture and its metadata:

- [`golden.json`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.json)
- [`golden.meta.json`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.meta.json)

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

- [Overview, thesis, proof metrics, and logical sequence](https://github.com/gmickel/flow-next/raw/main/.flow/assets/pr-aid/change-walkthrough-overview.jpeg)
- [Progressive disclosure from step to file to diff](https://github.com/gmickel/flow-next/raw/main/.flow/assets/pr-aid/change-walkthrough-expanded-diff.jpeg)
- [Grouped files, deliberate non-changes, and verification](https://github.com/gmickel/flow-next/raw/main/.flow/assets/pr-aid/change-walkthrough-grouped-files.jpeg)

Flow-Next approximates that hierarchy in GitHub Markdown. Richer consumers can
add interaction while preserving the semantic projection above.
