# PR cognitive-aid artifact

After the close commit and export, the existing host authors one v1 object from `EXPORT_PAYLOAD`, task
evidence and review receipts. No extra model call. Use the export's `MERGE_BASE` and `HEAD_SHA` throughout.

## Resolve, compose, validate

```bash
CURRENT_AID=$("$FLOWCTL" pr-cognitive-aid current "$SPEC_ID" --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA" --json)
```
Reuse status `current` exactly. Otherwise write one object to a private 0600 `AID_INPUT` tempfile outside the
repository:

- Identity: `schemaVersion: 1`, unique portable `artifactId`, `specId`, `baseSha`,
  `headSha`, UTC `generatedAt`; `supersedesArtifactId` names `latestArtifactId` if present.
- `sources[]` records have `id`, `kind`, `ref`; kinds `spec`, `task`, `rid`, `review_receipt`, `qa_receipt`,
  `diff_metadata`, `commit`, bound to this spec, its tasks, canonical R-IDs,
  receipts, commits and `$MERGE_BASE..$HEAD_SHA`. Include every declared R-ID, even uncovered.
- When export has `specs`, set `specIds` to their IDs in export order; keep `specId` as host. Declare every
  spec's requirements with qualified refs and `rIds` (`fn-250:R4`). At least one group per spec in review order
  (two allowed above ten must-read files), short ID in each title, using its task/evidence summary; no-spec commits get a group.
  Past the seven-step cap, merge the smallest specs into one group whose title names each short ID.
- `changeWalkthrough.thesis`: intent and approach. Optional authored strings:
  `userImpact` says what changes for a user or operator; `blastRadius` names who
  or what is touched, what to read first and what is unproven; `tradeoffs` records
  rejected alternatives reviewers would ask about; `openItems` records unfinished work.
- Unevidenced work belongs in `openItems`; required PR findings belong there or in Tradeoffs.
- `proof[]`: sourced `label`, `value`, `sourceRefs`, optional `outcome`.
  Draw from task evidence and review receipts: `pass` only for a gate run green,
  `fail` for failure, `unverified` for inconclusive or never-run steps, explaining
  the gap in `value`; no separate steps-not-verified field. Old outcome-less cells
  remain plain evidence, never gain a tick.
- QA receipts use `qa_outcome`, not the projected `verdict`: SHIP maps to pass,
  NEEDS_WORK to fail, BLOCKED/NA to unverified with their reason. Surface open
  findings in `openItems`, advisory only. Verify receipt head freshness against
  code, allowing only leading QA-receipt, lens and spec-close bookkeeping commits;
  stale/malformed receipts cannot justify a pass.
- Ordered `groups[]`: optional `problem`, optional `principle`, 1–7 `step`,
  optional `kept`, optional `verify`; author `ordinal`, `title`, `summary`, `sourceRefs`, `rIds`, `taskIds`.
  Group order is review order; `files` is required even when `[]`.
- Describe files a reviewer must read from `diff_summary.files[]`; let the rest be counted. Use
  `path`, `summary`, and `attentionClass` unless a state/lockfile/mirror pattern
  supplies it. Explicit classes win; canonical means must read, mechanical and
  generated mean safe to skim. References inherit from groups unless supplied;
  R-ID/task links need matching sources and files cite bound diff metadata.
- Omit mechanical `changeType`, `additions`, `deletions`, `diffUrl`; supplied
  values must validate. Flowctl-added empty-summary rows render in the counted
  “not described” line, not individual file rows. Never copy raw diff content.

Validate/write, `render --file` and `html-input --file` accept sparse input; persisted objects remain complete.
Correct validation errors together; never truncate values to evade validation or overwrite a generation.
```bash
# Dry-run: validation only, no repository writes.
"$FLOWCTL" pr-cognitive-aid validate --file "$AID_INPUT" --json
# Real create/update: validate and atomically persist.
"$FLOWCTL" pr-cognitive-aid write "$SPEC_ID" --file "$AID_INPUT" --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA" --json
```
Run only the matching command; reused artifacts need neither.

## Render

```bash
PR_AID_MARKDOWN=$("$FLOWCTL" pr-cognitive-aid render "$SPEC_ID" --base-sha "$MERGE_BASE" --head-sha "$HEAD_SHA") || PR_AID_MARKDOWN=""
# For a newly composed dry-run input, use instead:
PR_AID_MARKDOWN=$("$FLOWCTL" pr-cognitive-aid render --file "$AID_INPUT") || PR_AID_MARKDOWN=""
```
The renderer keeps authored content, showing at most 10 described rows per group; extra rows are counted.
A summary renders only with its row: nothing essential belongs only in row 11. There is no body budget
or need for a render-preview loop. Never merge export fields into the output. Invalid, stale or unsupported artifacts render nothing:
print one stderr note, set `PR_AID_CURRENT=false`, and use a labeled fallback with the export's goal, task
summaries, recorded verification and open items; never rejected fields. On success set `PR_AID_CURRENT=true`;
keep the immutable artifact local so it cannot move its own head. This phase ends before PR creation.
[create-and-finalize.md](create-and-finalize.md) creates the PR, then runs the tracker facade with `$PR_URL`.
