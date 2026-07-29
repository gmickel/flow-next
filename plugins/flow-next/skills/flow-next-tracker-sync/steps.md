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
body shape round-trips plain strings byte-exact. Persist an alternate version
only when discovery explicitly resolves it.

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

Linear MCP creation is allowed only as the MCP judgment surface. Pass its result
to `tracker persist-external`; the deterministic path completes the durable id
and local state.

Unlink reads the linked issue first, optionally synthesizes a short detached
comment, then atomically clears tracker state. Never rename or delete the Flow
spec.

## 3. Lifecycle facade input matrix

Content is written to secure temporary files. Create with mode `0600`, pass the
path, and delete it after the command.

| Operation | `flow-file` | `body-file` | `comments-file` | `source-body-file` |
|---|---|---|---|---|
| `push` | final Flow body | rendered tracker body | forbidden | forbidden |
| `pull` | final agent-folded Flow body | exact tracker snapshot used for the fold | normalized comment snapshot | forbidden |
| `reconcile` | final conflict-resolved Flow body | final tracker body | normalized comment snapshot | original tracker body used by the merge |
| `comment` | forbidden | synthesized comment text | forbidden | forbidden |

The facade owns create-if-unlinked, provider calls, status and relation
projection, marker dedup, paired snapshots, `lastSyncedAt`, and one aggregate
receipt. Do not reproduce those steps around the facade.

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

Comment bodies are synthesized by the caller. The facade owns stable markers,
deduplication, posting, and the receipt. Question-valve behavior and comment
normalization are documented in
[references/comments-sync.md](references/comments-sync.md).

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
specs by itself.

`list-relations` is read-only dependency ordering. `question` uses caller-owned
content synthesis and the comment marker contract. In autonomous mode, a
question is parked in tracker comments and resumed only from the matching
answer marker.

## 8. Completion

Confirm:

- one JSON envelope was consumed;
- one aggregate receipt exists for a lifecycle event;
- temporary content files were deleted;
- tracker state advanced only after verified remote success;
- any agentic conflict or recovery decision is recorded;
- no tracker action changed Flow task status.
