# PR cognitive-aid consumer contract

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts's own syntax and are quoted verbatim — do not convert them.


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

## Canonical fixture and downstream vendoring

Flow-Next owns the maximum-normal v1 fixture and its metadata:

- [`golden.json`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.json)
- [`golden.meta.json`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/tests/fixtures/pr-cognitive-aid/v1/golden.meta.json)

Metadata records `schemaVersion`, the upstream `sourcePath`, the full
`sourceCommit`, the immutable Git `sourceBlob`, the SHA-256 of the exact
`golden.json` bytes, and the executable performance contract. The blob and
SHA-256 are over the file bytes as checked in—not parsed/reformatted JSON.
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

- [Overview, thesis, proof metrics, and logical sequence](https://github.com/gmickel/flow-next/blob/main/.flow/assets/pr-aid/change-walkthrough-overview.jpeg)
- [Progressive disclosure from step to file to diff](https://github.com/gmickel/flow-next/blob/main/.flow/assets/pr-aid/change-walkthrough-expanded-diff.jpeg)
- [Grouped files, deliberate non-changes, and verification](https://github.com/gmickel/flow-next/blob/main/.flow/assets/pr-aid/change-walkthrough-grouped-files.jpeg)

Flow-Next approximates that hierarchy in GitHub Markdown. Richer consumers can
add interaction while preserving the semantic projection above.
