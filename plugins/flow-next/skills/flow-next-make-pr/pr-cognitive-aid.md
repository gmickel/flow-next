# PR cognitive-aid artifact

Run this phase after `export-cognitive-aid` succeeds and before HTML generation or
final PR-body composition. The existing host agent owns every judgment:
thesis, logical groups, summaries, order, and source attribution. This phase
adds no model call. `flowctl` only validates, persists, selects, and renders.

## 1. Resolve or compose

Use the code-under-review SHAs captured in pre-flight:

```bash
CURRENT_AID=$("$FLOWCTL" pr-cognitive-aid current "$SPEC_ID" \
  --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA" --json)
CURRENT_AID_STATUS=$(printf '%s' "$CURRENT_AID" | jq -r '.status')
CURRENT_AID_ID=$(printf '%s' "$CURRENT_AID" | jq -r '.artifact.artifactId // empty')
LATEST_AID_ID=$(printf '%s' "$CURRENT_AID" | jq -r '.latestArtifactId // empty')
```

When status is `current`, reuse that exact generation; do not compose a
parallel story. Render it in step 3.

Otherwise, compose exactly one JSON object from the already-loaded
`EXPORT_PAYLOAD`. Write it to a private temporary file (mode 0600) outside the
repository. The object follows `pr_cognitive_aid` schema version 1:

- Identity: `schemaVersion`, a portable unique `artifactId`, `specId`,
  `baseSha=$MERGE_BASE`, `headSha=$HEAD_SHA`, UTC `generatedAt`, and
  `supersedesArtifactId=$LATEST_AID_ID` when a prior chain tip exists.
- One bounded `sources[]` table. Allowed kinds: `spec`, `task`, `rid`,
  `review_receipt`, `qa_receipt`, `diff_metadata`, `commit`.
- `changeWalkthrough.thesis`, grounded `proof[]`, and ordered `groups[]`.
  Logical order: optional `problem`, optional `principle`, 1-7 `step`, optional
  `kept`, optional `verify`. Never invent an optional group.
- Each proof/group/file semantic claim carries non-empty `sourceRefs`.
  Group/file `rIds` and `taskIds` also carry a same-record source reference to
  the matching `rid` or `task` source. File claims do not inherit group claims.
- Each file comes only from `diff_summary.files[]`; keep its upstream group.
  `changeType` is Git state (`added|modified|deleted|renamed|copied`);
  `attentionClass` is review attention
  (`canonical|generated|mechanical`). Never collapse these dimensions.
- No raw diff text. `diffUrl` may be HTTPS or repository-relative only.

The validator enforces the full v1 payload, string, path, URL, provenance,
group, file, and byte bounds. Never pre-truncate to make invalid input pass.

## 2. Validate and persist before body creation

For `--dry-run`, validate without state change:

```bash
"$FLOWCTL" pr-cognitive-aid validate --file "$AID_INPUT" --json >/dev/null
```

For a real create/update, validation and immutable atomic publication are one
operation:

```bash
"$FLOWCTL" pr-cognitive-aid write "$SPEC_ID" --file "$AID_INPUT" \
  --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA" --json >/dev/null
```

The generation lands at
`.flow/artifacts/<spec-id>/pr-cognitive-aid/<artifactId>.json`. Never overwrite
or delete a prior generation. Failure is non-fatal for PR creation: print one
stderr note, set `PR_AID_CURRENT=false`, and use the existing legacy compact
body fields. Never partially render the rejected object.

## 3. Deterministic Markdown

For a reused/persisted generation:

```bash
PR_AID_MARKDOWN=$("$FLOWCTL" pr-cognitive-aid render "$SPEC_ID" \
  --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA") || PR_AID_MARKDOWN=""
```

For `--dry-run`, render the validated temporary file:

```bash
PR_AID_MARKDOWN=$("$FLOWCTL" pr-cognitive-aid render --file "$AID_INPUT") \
  || PR_AID_MARKDOWN=""
```

Non-empty output is inserted as one contiguous body section before Critical
changes. It is either:

- compact: thesis, proof, and one flat canonical-file table; or
- full when canonical additions+deletions are at least 200 or canonical file
  count is at least 6: complete legend, evidenced logical groups, file tables,
  and generated/mechanical rows collapsed inside their original group.

The rendered section never replaces or absorbs the separate risk-ranked
`## Review plan`, and never includes raw diff excerpts.

## 4. One truth, tracker boundary unchanged

When `PR_AID_MARKDOWN` is non-empty, the current v1 object is authoritative for
the thesis, proof metrics, R-ID/task links, verification claims, walkthrough
order, and file membership. Existing fields are fallback-only; never merge
stale/legacy values into those claims. Other established sections remain:
boundaries, Critical changes, How to review, Review plan, decisions, memory,
glossary/strategy, open items, QA, and the footer.

This phase ends before PR creation. Do not move or alter the post-creation
`makePr` tracker facade in `create-and-finalize.md`: `$PR_URL` must exist first;
the body tracker reference, explicit `--pr-url`, body-preserving In Review
reconcile, native link or deduplicated fallback, optional breadcrumb,
receipt-backed audit, and single bounded retro-fire all remain intact. Never
restore the retired tracker-runner dispatch.

## Done when

- Current matching v1 generation reused, or a new valid generation composed
  from the existing payload and validated before final body creation.
- Real run persisted one immutable generation; dry-run wrote no repository
  state.
- Markdown selected exactly one compact/full path and stayed separate from the
  Review plan.
- Rejection selected the labeled legacy fallback without mixing fields.
- No new model/network invocation; tracker creation/facade ordering unchanged.
