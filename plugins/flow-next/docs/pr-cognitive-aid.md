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
data. Raw diff text is not stored in the object.

Full validation rules, bounds, and fallback behavior are defined by the
[`pr-cognitive-aid` flowctl commands](flowctl.md#pr-cognitive-aid). The HTML
presentation boundary remains documented in
[`html-artifacts.md`](html-artifacts.md).

## Canonical fixture and downstream vendoring

Flow-Next owns the maximum-normal v1 fixture and its metadata:

- [`golden.json`](../tests/fixtures/pr-cognitive-aid/v1/golden.json)
- [`golden.meta.json`](../tests/fixtures/pr-cognitive-aid/v1/golden.meta.json)

Metadata records `schemaVersion`, the upstream `sourcePath`, the full
`sourceCommit`, and the SHA-256 of the exact `golden.json` bytes. The digest is
over the file bytes as checked in—not parsed/reformatted JSON.

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
