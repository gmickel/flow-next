# PR cognitive-aid artifact

After close and export, the host authors one v1 object from `EXPORT_PAYLOAD` and evidence; no extra model call.
Use `diff_summary.merge_base_sha` / `diff_summary.head_sha` as `MERGE_BASE` / `HEAD_SHA`.
Per-task evidence is under `specs[].tasks[]` (or the host's `tasks`), not `tasks_summary`.

## Resolve, compose, validate

```bash
CURRENT_AID=$("$FLOWCTL" pr-cognitive-aid current "$SPEC_ID" --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA" --json)
```
Reuse `current` exactly; otherwise author a private 0600 `AID_INPUT` tempfile outside the repository.
Replace skeleton identities, paths and evidence with export values; declare every R-ID, even uncovered:
```json
{"schemaVersion":1,"artifactId":"aid-001","specId":"fn-136-cognitive-aid","specIds":["fn-136-cognitive-aid"],"baseSha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","headSha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","generatedAt":"2026-09-21T12:00:00Z",
 "sources":[{"id":"spec","kind":"spec","ref":"fn-136-cognitive-aid"},{"id":"task","kind":"task","ref":"fn-136-cognitive-aid.1"},{"id":"rid","kind":"rid","ref":"R6"},{"id":"row-rid","kind":"rid","ref":"R7"},{"id":"review","kind":"review_receipt","ref":".flow/receipts/review.json"},{"id":"qa","kind":"qa_receipt","ref":".flow/receipts/qa.json"},{"id":"diff","kind":"diff_metadata","ref":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa..bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},{"id":"commit","kind":"commit","ref":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}],
 "changeWalkthrough":{"thesis":"Keep review grounded in the changed files.","userImpact":"Reviewers get a reading order.","blastRadius":"Read the validator first.","tradeoffs":"Keep provenance in the artifact.","openItems":"Live verification remains unverified.",
 "groups":[{"ordinal":1,"kind":"problem","title":"Review context","summary":"Check the intended review boundary.","sourceRefs":["spec"],"rIds":[],"taskIds":[],"files":[]},{"ordinal":2,"kind":"step","title":"Validate and render","summary":"Check validation before reviewing output.","sourceRefs":["spec","task","rid","row-rid","diff"],"rIds":["R6"],"taskIds":["fn-136-cognitive-aid.1"],"files":[{"path":"src/change_0.py","summary":"Validates the briefing.","attentionClass":"canonical","rIds":["R7"]}]}],
 "proof":[{"label":"Review","value":"Passed at the bound head","sourceRefs":["review"],"outcome":"pass"},{"label":"Render time","value":"12 ms","sourceRefs":["task"]}]}}
```
Use a unique portable `artifactId`; optional `supersedesArtifactId` names `latestArtifactId`.
Export `tasks[].evidence.commits` are SHORT SHAs: expand with `git rev-parse` before citing full 40-hex commit refs.

- When export has `specs`, set `specIds` to their IDs in export order; keep `specId` as host. Declare every
  spec's requirements with qualified refs and `rIds` (`fn-250:R4`). At least one group per spec in review order
  (two allowed above ten must-read files), short ID in each title, using its task/evidence summary; no-spec commits get a group.
  Past the seven-step cap, merge the smallest specs into one group whose title names each short ID.
- `changeWalkthrough.thesis`: intent and approach. Optional authored strings:
  `userImpact` describes user/operator changes; `blastRadius` names scope, reading order and what is unproven;
  `tradeoffs` records rejected alternatives; `openItems` records unfinished work.
- Unevidenced work belongs in `openItems`; required PR findings belong there or in Tradeoffs.
- `proof[]` has at most 16 cells with `label` and `value` (each at most 160 characters), `sourceRefs`, and optional `outcome`.
  Use `pass` for a known green gate, `fail` for failure, `unverified` for inconclusive or never-run steps with the gap in `value`.
  A passed gate without a stored receipt cites the merge commit or pull request that carried it (a `review_receipt` ref can be its URL).
  Omit `outcome` only for a recorded fact that is neither passed nor failed, such as a measurement; it renders as a plain item.
- QA receipts use `qa_outcome`, not the projected `verdict`: SHIP maps to pass,
  NEEDS_WORK to fail, BLOCKED/NA to unverified with their reason. Open findings go in `openItems`, advisory only.
  Verify head freshness against code, allowing only leading QA-receipt, lens and spec-close bookkeeping commits;
  stale/malformed receipts cannot justify a pass.
- At most 11 ordered `groups[]`: optional `problem`, optional `principle`, 1–7 `step`,
  optional `kept`, optional `verify`; author `ordinal`, `title`, `summary`, `sourceRefs`, `rIds`, `taskIds`.
  Group order is review order; `files` is required even when `[]`. Group `summary` renders "what to check here" in one or two sentences.
  Each file belongs to exactly one group: use the first whose review needs it, cite other specs' requirement IDs on its row and name those specs in its summary.
- Describe files a reviewer must read from `diff_summary.files[]`; let the rest be counted. Use
  `path`, `summary`, and `attentionClass` unless a state/lockfile/mirror pattern supplies it. Explicit classes win.
  Canonical means must read; mechanical/generated mean safe to skim.
  Unlisted canonical paths appear under Rest of diff; spec/task markdown under `.flow/` is canonical: describe it or class it mechanical.
  Every id in a record's `rIds`/`taskIds` needs its source id in that record's effective `sourceRefs`.
  For an id its group does not cite, add the source to the group's `sourceRefs`, or give the row complete `sourceRefs`, including its task and diff sources.
  A row inherits group references unless it supplies its own; its nonempty `rIds` alone determine displayed tags.
- Omit mechanical `changeType`, `additions`, `deletions`, `diffUrl`; supplied
  values must validate. Added empty-summary rows count as “not described”. Never copy raw diff content.

Sparse input works with validate/write and both `--file` readers; storage stays complete. Fix errors together; never truncate or overwrite.
Use `validate` only for dry-run; real runs call `write` directly, which validates.
```bash
"$FLOWCTL" pr-cognitive-aid validate --file "$AID_INPUT" --json
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
The renderer keeps authored sections and every group's title and summary; at most 10 described rows per group, with extra rows counted.
Keep essential guidance above row 11; no body budget or preview loop. Never merge export fields into rendered output.
Invalid, stale or unsupported artifacts render nothing: print a stderr note and set `PR_AID_CURRENT=false`.
Write a labeled fallback from the export's goal, tasks, verification and open items to `BODY_FILE`, excluding rejected fields.
On success set `PR_AID_CURRENT=true`.
Keep the immutable artifact local. Next, [create-and-finalize.md](create-and-finalize.md) creates the PR and runs the tracker facade with `$PR_URL`.
