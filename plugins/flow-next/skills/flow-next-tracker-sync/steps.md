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
tag, except pull and reconcile: their body preparation (§4) exists only in the
facade, so a manual one calls it with `--event manual`. Otherwise the `tracker
sync` facade always receives the caller's real event key; never invoke it
without `--event`.

All autonomous signals collapse into one no-prompt gate:

```bash
UNATTENDED=0
[[ "${FLOW_AUTONOMOUS:-}" == "1" || "${AUTONOMOUS:-}" == "1" \
   || "$ARGUMENTS" == *mode:autonomous* ]] \
  && UNATTENDED=1
```

`UNATTENDED=1` means any unattended run. A lifecycle stage that
runs the inline wrapper applies its own autonomy: a stage `flow --auto`
dispatched carries `mode:autonomous`, so it takes the `UNATTENDED=1` path.

> **Autonomy parity is a hard invariant.** Under `UNATTENDED=1` no code path reaches
> `AskUserQuestion`: discovery, collisions, merge conflicts, and question
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
2 is the default for both Cloud and Data Center/Server; flowctl converts bodies
to v2 wiki markup, which needs the Wiki Style Renderer on the body fields
([references/jira.md](references/jira.md)). Discovery persists version 2;
alternate API versions are unsupported.

**Done when:** `tracker resolve` returned a destination that was shown for
confirmation, the confirmed non-secret configuration is persisted, and no
credential landed in `.flow/config.json`. Under `UNATTENDED=1` discovery deferred for
a human instead — the transcript shows no `AskUserQuestion` on this path.

## 2. Identity and linking

Three supported starts share one durable locator:

- **Flow-first:** create an issue for an existing spec, then persist the durable
  id, display identifier, and URL.
- **Tracker-first:** read the existing issue, mint the hybrid Flow id linked
  (`spec create --tracker-first --tracker-id --tracker-url`), and seed the
  paired merge base from the current bodies.
- **Create-first:** create a remote issue using a retry key before a local spec
  exists, then mint linked from the returned identity. If local persistence
  fails after the remote create, retry links the recovery record and never
  creates a duplicate.

Before any remote create (create-first, or a Flow-first issue create), a retry or recovery of
one, or linking an existing issue that needs a back-reference: read
[references/create-first.md](references/create-first.md) for the retry-key receipt contract and
the back-reference rule.

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
| `push` | optional (defaults to current spec) | optional (flowctl renders) | forbidden | forbidden | optional synthesized comment | forbidden |
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

For push, invoke `tracker sync <spec> --op push --event <event>` directly.
Flowctl reads the current spec and renders every section deterministically;
`--status-only` also needs no content file. Explicit file inputs remain valid.

For pull or reconcile, first invoke:

```bash
$FLOWCTL tracker sync "$SPEC_ID" --op "$OP" --event "$EVENT" --prepare --json
```

Use `classification`, `tracker_body`, the paired `base`, and
`genuine_comments` from that response. `files` holds mode-0600 snapshots:
`flow_file`, `body_file`, `source_body_file`, `comments_file`, and `base_file`.
The comment snapshot includes all comments for the facade's unchanged CAS check;
only `genuine_comments` are candidates for the host's fold. Do not replace that
snapshot with the filtered list. Snapshots are removed after the next facade
operation for this spec, or swept once expired (one hour) on the next prepare.

`noop`/echo and `flow-only` comparisons need no body judgment. With no genuine
comments, use the unchanged Flow file for a noop pull; for reconcile's
`flow-only` class call push without body inputs. A pull never pushes local
changes. `tracker-only`, `both-changed`, and `no-base` use the three-way merge in
[references/body-merge.md](references/body-merge.md) to author the final Flow
fold and, for reconcile, the final tracker body. Keep the original snapshot
files intact; put authored output in separate mode-0600 files. Apply the final
Flow body locally before the facade call and pass the full original comment
snapshot. Pull never changes Flow task status.

With `tracker.specWins: true`, make-pr's reconcile (event `makePr`) needs no
body merge: the Flow file is the current spec plus any genuine-comment fold,
and flowctl sends the rendered spec as the final tracker body.

A true section conflict remains host judgment: show the section and both edits,
then ask in attended mode. Any autonomy marker (`FLOW_AUTONOMOUS=1`, `AUTONOMOUS=1`, or
`mode:autonomous`, including the calling stage's marker) or a fork uses
`flowctl sync defer` instead.

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

A push `conflict` with subtype `tracker_diverged` means someone edited the
tracker body since the last sync. With `UNATTENDED=0` outside a forked call, ask once: reconcile
(recommended, merges both sides), overwrite the tracker body (rerun the same
push with `--overwrite-diverged`), or leave it. With `UNATTENDED=1` (including every
stage `flow --auto` runs) or in a forked call, never overwrite: record it with
`flowctl sync defer <spec-id> --summary "tracker body diverged since last sync"
--suggested "reconcile, or confirm an --overwrite-diverged push"` and continue.

Recovery routing is agentic because the same class can imply a user choice,
MCP continuation, local correction, or deferral. The error message is
diagnostic prose, never a routing API.

## 7. Backlog and question operations

Only for `wire list-open`, `comment-list`, `relation-list` or `question` (backlog enumeration,
dependency ordering, parked questions): read [references/backlog-ops.md](references/backlog-ops.md).

## 8. Completion

Confirm:

- one JSON envelope was consumed;
- one aggregate receipt exists for a lifecycle event;
- temporary content files were deleted;
- tracker state advanced only after verified remote success;
- any agentic conflict or recovery decision is recorded;
- no tracker action changed Flow task status.
