# PR cognitive-aid artifact

After close and export, the host authors one v1 object from `EXPORT_PAYLOAD` and evidence; no extra model call.
Use `diff_summary.merge_base_sha` / `diff_summary.head_sha` as `MERGE_BASE` / `HEAD_SHA`.
Per-task evidence is under `specs[].tasks[]` (or the host's `tasks`), not `tasks_summary`.

## Resolve, compose, validate

```bash
CURRENT_AID=$("$FLOWCTL" pr-cognitive-aid current "$SPEC_ID" --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA" --json)
```
Reuse status `current` exactly. Otherwise write one object to a private 0600 `AID_INPUT` tempfile outside the
repository:

Use this sparse skeleton, replacing example identities, paths and evidence with the export's values:
```json
{"schemaVersion":1,"artifactId":"aid-001","specId":"fn-136-cognitive-aid","specIds":["fn-136-cognitive-aid"],"baseSha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","headSha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","generatedAt":"2026-09-21T12:00:00Z",
 "sources":[{"id":"spec","kind":"spec","ref":"fn-136-cognitive-aid"},{"id":"task","kind":"task","ref":"fn-136-cognitive-aid.1"},{"id":"rid","kind":"rid","ref":"R6"},{"id":"review","kind":"review_receipt","ref":".flow/receipts/review.json"},{"id":"qa","kind":"qa_receipt","ref":".flow/receipts/qa.json"},{"id":"diff","kind":"diff_metadata","ref":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa..bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},{"id":"commit","kind":"commit","ref":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}],
 "changeWalkthrough":{"thesis":"Keep review grounded in the changed files.","userImpact":"Reviewers get a reading order.","blastRadius":"Read the validator first.","tradeoffs":"Keep provenance in the artifact.","openItems":"Live verification remains unverified.",
 "groups":[{"ordinal":1,"kind":"step","title":"Validate and render","summary":"Check validation before reviewing output.","sourceRefs":["spec","task","rid","diff"],"rIds":["R6"],"taskIds":["fn-136-cognitive-aid.1"],"files":[{"path":"src/change_0.py","summary":"Validates the briefing.","attentionClass":"canonical","rIds":["R6"]}]}],
 "proof":[{"label":"Review","value":"Passed at the bound head","sourceRefs":["review"],"outcome":"pass"},{"label":"Render time","value":"12 ms","sourceRefs":["task"]}]}}
```
Use a unique portable `artifactId`; optional `supersedesArtifactId` names `latestArtifactId`.
Source records use `id`, `kind`, `ref`; commit refs are full 40-hex SHAs. Include every declared R-ID, even uncovered.

- When export has `specs`, set `specIds` to their IDs in export order; keep `specId` as host. Declare every
  spec's requirements with qualified refs and `rIds` (`fn-250:R4`). At least one group per spec in review order
  (two allowed above ten must-read files), short ID in each title, using its task/evidence summary; no-spec commits get a group.
  Past the seven-step cap, merge the smallest specs into one group whose title names each short ID.
- `changeWalkthrough.thesis`: intent and approach. Optional authored strings:
  `userImpact` describes user/operator changes; `blastRadius` names scope, reading order and what is unproven;
  `tradeoffs` records rejected alternatives; `openItems` records unfinished work.
- Unevidenced work belongs in `openItems`; required PR findings belong there or in Tradeoffs.
- `proof[]` uses `label` and `value` (each at most 160 characters), `sourceRefs`, and optional `outcome`.
  Use `pass` for a known green gate, `fail` for failure, `unverified` for inconclusive or never-run steps with the gap in `value`.
  A passed gate without a stored receipt cites the merge commit or pull request that carried it (a `review_receipt` ref can be its URL).
  Omit `outcome` only for a recorded fact that is neither passed nor failed, such as a measurement; it renders as a plain item.
- QA receipts use `qa_outcome`, not the projected `verdict`: SHIP maps to pass,
  NEEDS_WORK to fail, BLOCKED/NA to unverified with their reason. Open findings go in `openItems`, advisory only.
  Verify head freshness against code, allowing only leading QA-receipt, lens and spec-close bookkeeping commits;
  stale/malformed receipts cannot justify a pass.
- Ordered `groups[]`: optional `problem`, optional `principle`, 1–7 `step`,
  optional `kept`, optional `verify`; author `ordinal`, `title`, `summary`, `sourceRefs`, `rIds`, `taskIds`.
  Group order is review order; `files` is required even when `[]`. Group `summary` renders "what to check here" in one or two sentences.
  Each file belongs to exactly one group: use the first whose review needs it, cite other specs' requirement IDs on its row and name those specs in its summary.
- Describe files a reviewer must read from `diff_summary.files[]`; let the rest be counted. Use
  `path`, `summary`, and `attentionClass` unless a state/lockfile/mirror pattern supplies it. Explicit classes win.
  Canonical means must read; mechanical/generated mean safe to skim. References inherit unless supplied.
  A row with its own nonempty `rIds` shows only those. R-ID/task links need matching sources; files cite bound diff metadata.
- Omit mechanical `changeType`, `additions`, `deletions`, `diffUrl`; supplied
  values must validate. Added empty-summary rows count as “not described”. Never copy raw diff content.

Sparse input works with validate/write, `render --file` and `html-input --file`; storage stays complete.
Correct errors together; never truncate values or overwrite a generation. On real runs, call `write` directly: it validates.
```bash
# Dry-run: validation only, no repository writes.
"$FLOWCTL" pr-cognitive-aid validate --file "$AID_INPUT" --json
# Real create/update: validate and atomically persist.
"$FLOWCTL" pr-cognitive-aid write "$SPEC_ID" --file "$AID_INPUT" --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA" --json
```
Run only the matching command; reused artifacts need neither.

## Render

Create a private 0600 `BODY_FILE` tempfile. Render once, redirecting stdout directly to it:
```bash
"$FLOWCTL" pr-cognitive-aid render "$SPEC_ID" --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA" > "$BODY_FILE"
# Newly composed dry-run input: use this instead.
"$FLOWCTL" pr-cognitive-aid render --file "$AID_INPUT" > "$BODY_FILE"
```
The renderer keeps authored content, showing at most 10 described rows per group; extra rows are counted.
Nothing essential belongs only in row 11. There is no body budget or render-preview loop. Never merge export fields into output. Invalid, stale or unsupported artifacts render nothing:
print one stderr note, set `PR_AID_CURRENT=false`, and use a labeled fallback with the export's goal, task
summaries, recorded verification and open items, written to `BODY_FILE`; never rejected fields. On success set `PR_AID_CURRENT=true`.
Keep the immutable artifact local. Next, [create-and-finalize.md](create-and-finalize.md) creates the PR and runs the tracker facade with `$PR_URL`.
