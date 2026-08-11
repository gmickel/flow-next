# Tracker-sync operation sequence

This file documents the inputs, outputs, and judgment handoffs around
`flowctl tracker`. It contains no provider invocation recipes. The executable
contract is the CLI and `flowctl_tracker` package.

## 0. Route and gate

Read one configuration snapshot. If the bridge is inactive, lifecycle callers
return silently. If active, read the selected `perEvent` value and map it:

| Configured value | Lifecycle facade operation |
|---|---|
| `off` | no call |
| `pull` | `pull` |
| `push` | `push` |
| `reconcile` | `reconcile` |
| `comment` | `comment` |

Callers with stricter event contracts retain them. QA maps every non-`off`
value to `comment`. Work events use their fixed operation. Make PR and the
successful land merge have their documented unconditional active-bridge paths.

Manual runs use the matching granular `flowctl tracker` verb and carry no event
tag. The `tracker sync` facade is event-only and always receives the caller's
real event key; never invoke that facade without `--event`.

All autonomous signals collapse into one no-prompt gate:

```bash
RALPH=0
[[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
 || "${FLOW_AUTONOMOUS:-}" == "1" || "$ARGUMENTS" == *mode:autonomous* ]] \
 && RALPH=1
```

> **Autonomy parity is a hard invariant.** Under `RALPH=1` no code path reaches
> `plain-text numbered prompt`: discovery, collisions, merge conflicts, and question
> authoring defer for a human instead of prompting.

## 1. Discovery

Discovery is the one-time agentic ceremony:

1. Surface detected and absent provider signals.
2. Resolve environment choice before stored configuration.
3. Ask only when provider, project, team, or lifecycle defaults are ambiguous.
4. Persist confirmed non-secret configuration.
5. Run `tracker resolve`.
6. Show the resolved destination and capabilities for confirmation.

No confirmation means no write. Credentials stay outside `.flow/config.json`.
For Jira, persist the deployment shape selected during discovery. API version
2 is the default for both Cloud and Data Center/Server because the measured v2
body shape round-trips plain strings byte-exact. Discovery persists version 2;
alternate API versions are unsupported.

**Done when:** `tracker resolve` returned a destination that was shown for
confirmation, the confirmed non-secret configuration is persisted, and no
credential landed in `.flow/config.json`. Under `RALPH=1` discovery deferred for
a human instead — the transcript shows no `plain-text numbered prompt` on this path.

## 2. Identity and linking

Three supported starts share one durable locator:

- **Flow-first:** create an issue for an existing spec, then persist the durable
 id, display identifier, and URL.
- **Tracker-first:** read the existing issue, mint the hybrid Flow id, link it,
 and seed the paired merge base from the current bodies.
- **Create-first:** create a remote issue using a retry key before a local spec
 exists, mint from the returned identity, then link. If local persistence
 fails after the remote create, retry links the recovery record and never
 creates a duplicate.

#### Receipt / retry contract

Before creating remotely, derive the first 16 hex characters of
`sha256(type NUL title NUL body)` with `sync create-first-key`, then query that
key with `sync create-first-get`. A hit resumes by linking the recorded issue;
it never creates another.

After a successful remote create, immediately persist the returned identity
with `sync create-first-put`. Keep that recovery record across any later
failure. **After minting the local spec, record the claim with
`sync create-first-put --spec-id <id> --if-absent` (fn-182, #310)** - the CAS
form, so two promoters racing on the same candidate end with one recorded
spec. On exit `10` with `subtype=spec_already_minted`, another promoter won:
adopt `details.recordedSpecId` and discard the locally minted spec - never
re-put. On `subtype=record_missing`, the candidate was already promoted and
cleared (or never recorded here): locate the issue's attached spec via the
tracker id and adopt it. Only after mint, attach, merge-base seed,
back-reference, and the normal spec-keyed receipt all succeed may the caller
consume the record with `sync create-first-clear`. These four helpers
exclusively own the retry record; do not recompute its hash or read, write, or
delete its file directly.

**Back-reference:** write `flow:<spec-id>` only after the durable local link
exists. A failed back-reference leaves the recovery record available for a
safe retry.

Linear MCP creation is allowed only as the MCP judgment surface. Pass its result
to `tracker persist-external`; the deterministic path completes the durable id
and local state.

Unlink reads the linked issue first, optionally synthesizes a short detached
comment, then atomically clears tracker state. Never rename or delete the Flow
spec.

## 3. Lifecycle facade input matrix

Content is written to secure temporary files. Create with mode `0600`, pass the
path, and delete it after the command.

| Operation | `flow-file` | `body-file` | `comments-file` | `source-body-file` | `comment-file` | `pr-url` |
|---|---|---|---|---|---|---|
| `push` | final Flow body | rendered tracker body | forbidden | forbidden | optional synthesized comment | forbidden |
| `pull` | final agent-folded Flow body | exact tracker snapshot used for the fold | normalized comment snapshot | forbidden | forbidden | forbidden |
| `reconcile` | final conflict-resolved Flow body | final tracker body | normalized comment snapshot | original tracker body used by the merge | forbidden | optional only for event `makePr` |
| `comment` | forbidden | synthesized comment text | forbidden | forbidden | forbidden | forbidden |

Every synthesized comment input (`comment` body or push `comment-file`) starts
with `evidence=<token>`. The caller chooses a stable, whitespace-free identity
for that occurrence — task/evidence commit, reviewed or tested head, spec
content fingerprint, or merge commit. Missing, empty, or placeholder evidence
is invalid input; never reuse one fallback token across repeatable events.

The facade owns create-if-unlinked, provider calls, status and relation
projection, marker dedup, paired snapshots, `lastSyncedAt`, and one aggregate
receipt. Do not reproduce those steps around the facade.

**Done when:** every file column matches the operation's row, each temporary
file was mode `0600` and is deleted after the call, each synthesized comment
file opens with a stable non-placeholder `evidence=<token>` line, and the
lifecycle event left exactly one aggregate receipt — not a second receipt
written around the facade.

## 4. Body preparation

For push, render the tracker body from the Flow spec without changing Flow.

For pull, compare the exact tracker snapshot with Flow and the stored base.
Produce the final Flow body using
[references/body-merge.md](references/body-merge.md). Pull never changes Flow
task status.

For reconcile, use the three-way merge reference. Automatic non-conflicting
folds are acceptable. A true section conflict is retained as the body-merge
judgment surface: show the section and both edits, then ask in interactive
mode. Under Ralph or a fork, defer it.

Flow-owned dependency marker blocks are excluded at the comparison boundary.
The exact server readback becomes the tracker-side base after a successful
write.

## 5. Status, relations, and comments

Status rules are deterministic and live in
[references/status-sync.md](references/status-sync.md). A requested target is
input to the policy, not authority to overwrite the tracker.

Dependency projection uses `tracker relate`. It is direct-edge only,
additive, and provenance-led. A missing remote relation that Flow previously
recorded is a conflict to defer, not permission to recreate it.

Comment bodies and their stable `evidence=<token>` occurrence identities are
synthesized by the caller. The facade owns stable markers, deduplication,
posting, and the receipt. Question-valve behavior and comment normalization are
documented in
[references/comments-sync.md](references/comments-sync.md).

Make PR passes its just-created absolute PR URL as `--pr-url`. The reconcile
facade owns the provider projection: GitHub's PR-body `Refs #N`, a deduplicated
GitLab note, a Jira remote-link upsert with comment fallback, or Linear's rich
URL attachment. Merge evidence supplies lifecycle state only; never infer link
content from it.

## 6. Structured recovery

Branch only on the envelope:

| Class | Routing |
|---|---|
| `inactive` | lifecycle caller stays silent |
| `rate_limited` | retry only when `retryable` is true; honor `retry_after_s` |
| `auth` | surface the provider credential requirement; do not mutate state |
| `unresolved` | run or request discovery/resolution for the named scope |
| `stale_id` | refresh the locator; never write through a mismatched parent |
| `not_found` | ask whether to relink or detach; never silently recreate |
| `capability` | report the typed capability and documented degradation |
| `conflict` | use typed candidates or conflict details; ask or defer |
| `invalid_input` | correct local inputs; do not retry unchanged |
| `transport` | preserve state and report; retry only when explicitly allowed |
| `external_action_required` | perform the named MCP action if authorized, then resume with `persist-external`; otherwise defer |

Recovery routing is agentic because the same class can imply a user choice,
MCP continuation, local correction, or deferral. The error message is
diagnostic prose, never a routing API.

## 7. Backlog and question operations

Backlog enumeration uses the deterministic `wire list-open` contract and the
resolved ready lane. It returns normalized issues only. It does not create Flow
specs by itself. On Linear with `tracker.readyState` unset, `list-open` refuses
with an `unresolved`/`ready_state` error (fn-182, #311): treat that refusal as
"no ready lane configured" and fall back to Flow-ready specs - it is not an
empty board and not a transport failure.

For each returned issue, build its locator from the same normalized row
(`durable = issue.id`, `display = issue.identifier`). `list-comments` is the
read-only parked-question call:

```bash
$FLOWCTL tracker wire comment-list --locator "$LOCATOR" --json
```

It returns normalized `created_at` timestamps. Reject truncated listings.
When the same stable question id has both question and answer markers, compare
their immutable timestamps: latest question means parked; latest answer means
answered. Missing or tied chronology fails closed.

`list-relations` is the read-only dependency-ordering call:

```bash
$FLOWCTL tracker wire relation-list --locator "$LOCATOR" --json
```

Treat `class: transport`, `subtype: truncated` as a failed read and route it
through normal structured-error recovery. Never order work from a partial
dependency graph.

For `question`, the caller owns the semantic body and the four stable identity
inputs. Write only the free-prose body to a mode `0600` temporary file. The wire
verb computes the id, adds the canonical marker, lists existing comments, and
posts only when the latest round for that id is answered or no question exists:

```bash
$FLOWCTL tracker wire question --locator "$LOCATOR" \
 --subject-id "$SUBJECT_ID" --blocked-stage "$BLOCKED_STAGE" \
 --reason-code "$REASON_CODE" --question-slug "$QUESTION_SLUG" \
 --body-file "$BODY_FILE" --json
```

Before listing, flowctl takes a local claim keyed by provider, durable issue id,
and stable question id; it releases the claim after dedup/post. A concurrent
identical ask returns retryable `question_in_flight`, then deduplicates against
the winner on retry.

`SUBJECT_ID` is the spec id for a spec-backed item and the normalized durable
`issue.id` for a tracker-only item; never use the display key in the hash.
Spec-backed questions also write the returned `data.question_id` into the
matching `## Open Questions` anchor. A tracker-only question has no local
receipt or spec write. In autonomous mode, a question resumes only from the
matching answer marker. If no tracker transport exists, retain the existing
spec-only floor; a tracker-only subject has nowhere durable to park and returns
`NEEDS_HUMAN`.

## 8. Completion

Confirm:

- one JSON envelope was consumed;
- one aggregate receipt exists for a lifecycle event;
- temporary content files were deleted;
- tracker state advanced only after verified remote success;
- any agentic conflict or recovery decision is recorded;
- no tracker action changed Flow task status.
