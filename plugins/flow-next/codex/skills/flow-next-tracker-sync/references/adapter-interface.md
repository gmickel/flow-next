# Tracker adapter contract

The executable contract lives in `flowctl_tracker`. This reference documents
the transport-independent shapes consumed by the lifecycle facade.

## Locator

Every issue-addressed verb receives:

```json
{"durable": "provider-stable-id", "display": "human identifier"}
```

The durable id is the dedup and stale-parent key. The display value is the
provider address: `#N`, `project#iid`, or `KEY-N`. Before every mutation,
flowctl reads the parent and compares the returned durable id. A mismatch is
`class: conflict`; no mutation is sent.

## Normalized issue

```json
{
 "id": "durable id",
 "identifier": "display key",
 "url": "canonical URL",
 "title": "plain text",
 "body": "markdown",
 "status": {"id": "provider id", "name": "provider name", "slot": "in_progress"},
 "labels": ["label"],
 "assignees": [{"id": "provider id", "name": "display name"}],
 "updatedAt": "provider timestamp"
}
```

Missing provider fields normalize to `null` or an empty collection. Adapters do
not manufacture identity fields absent from a provider response.

## Normalized wire comment

```json
{
 "id": "provider comment id",
 "body": "plain markdown",
 "url": "provider URL or null",
 "created_at": "immutable provider timestamp or null",
 "raw": {},
 "parent_identity": "validated or not_available"
}
```

`parent_identity` records whether the adapter verified the parent from a real
provider field. It is never inferred. The facade's `comments-file` snapshot is
the stable subset `id`, `body`, and `parent_identity`.

`created_at` preserves the provider's immutable creation timestamp so
question/answer rounds can be ordered independently of provider list order.
Comment authors and question/answer marker meaning belong to the semantic
comment layer. The closed marker vocabulary and Sync Log rules are documented
in [comments-sync.md](comments-sync.md); flowctl owns sync marker formatting,
normalization, and deduplication.

## Wire verbs

| Verb | Input | Output | Local state |
|---|---|---|---|
| `read` | locator | normalized issue | none |
| `update` | locator, optional title/body | normalized issue | none |
| `comment-add` | locator, body file | normalized comment | none |
| `comment-list` | locator | normalized comment list | none |
| `comment-update` | locator, comment id, body file | normalized comment | none |
| `comment-delete` | locator, comment id | deletion result | none |
| `label` | locator, add/remove names | normalized labels | none |
| `assign` | locator, add/remove ids | normalized assignees | none |
| `list-open` | resolved ready lane | normalized issue list | Linear, unset `tracker.readyState`: `unresolved`/`ready_state` refusal (treat as no-ready-lane, not empty board; fn-182 #311) |
| `attach` | locator, file | attachment metadata | none |
| `attach-get` | attachment id, output path | retrieved metadata | output file only |

Pagination is exhausted inside the adapter. Consumers never receive a provider
cursor or page token.

## Lifecycle verbs

Lifecycle verbs are subject-aware (typed subjects: `spec`, `chart`,
`decision`). They may update the linked tracker block on that subject and
write one receipt:

- `create` creates and links an issue for an existing subject.
- `create-first` creates before a subject and writes retry-key recovery state.
- `persist-external` records an authorized MCP result.
- `status` applies the deterministic status policy (specs; chart claim/release
 never masquerades as provider workflow status).
- `relate` projects one blocked-by edge with provenance.
- `sync-body` performs write/readback and paired merge-base persistence.
- `sync` composes the event lifecycle as one unit.
- Chart projection reuses the same facade with subject kind `chart` /
 `decision` (see Chart subjects below).

## Chart subjects (fn-135)

Optional when `tracker.charts` is the literal `on` and the bridge is active.
`.flow/charts/` remains canonical; remote state is an idempotent projection.

### Parent / child locator

| Subject | Kind | Locator storage | Remote shape |
|---|---|---|---|
| Chart | `chart` | chart JSON `tracker.{id,identifier,url}` | Parent issue |
| Decision | `decision` | decision JSON `tracker.{id,identifier,url}` | Child issue |

Locators are never chart identity. Durable id is the dedup and stale-parent
key across **all** subject kinds (specs, charts, decisions). Retry after
remote create but before local ledger publication completes the same identity
via the event marker + revision key.

### Hierarchy capability

| Capability | Lossless form | Degraded form |
|---|---|---|
| `subIssues` true (GitHub) | Native parent/child (`sub_issues`): chart = parent, decision = child | n/a |
| `subIssues` false (Linear, GitLab, Jira) | n/a | Labelled/linked flat issues; result reports `degraded.capability=subIssues`, `form=flat_linked` |

### Blocking projection

| Local edge | Remote projection |
|---|---|
| `blocked_by[]` | Native blocking relation **only** when `blockedBy` capability is true (Linear, Jira; GitLab when plan-gated probe says so). |
| `depends_on[]` | **Never** projected as an indistinguishable blocking edge. Local provenance only unless a future lossless distinct relation exists. Result stays silent on depends_on remote edges. |
| GitHub | No blocked-by; hierarchy is not a substitute for blocking. `blocked_by` stays local + owned body text; `degraded.capability=blockedBy`. |

### Decision child fields (lossless vs owned body)

Project through native fields/labels when lossless; otherwise an owned body
block (`<!-- flow-next:decision -->` ... `<!-- /flow-next:decision -->`) with
explicit degradation:

- D-ID, title, type, attendance, local status
- Safe resolution gist (never full answer bodies)
- Approved evidence references only (repo-relative paths, branch/commit refs,
 approved HTTPS URLs)
- Claim/release may refresh the owned block/counts; **never** maps to provider
 workflow status

Never copy: full answers, unsafe assets, credentials, acceptance-criterion
source tags.

### Parent rollup (compact only)

Owned block `<!-- flow-next:chart-rollup -->` ... carries:

- Chart Outcome and status
- Counts: actionable, blocked, claimed, resolved, superseded, out-of-scope, parked
- Latest resolved D-ID / title / safe gist
- Current frontier summary

### Lifecycle events (local-first, receipt-backed)

Each committed local revision produces one idempotent event marker + one
aggregate receipt. Events: `chart.create`, `chart.wire`, `chart.claim`,
`chart.release`, `chart.resolve`, `chart.supersede`, `chart.outOfScope`,
`chart.briefing`, `chart.abandon`, `chart.reopen`, `chart.staleLink`.

Partial / failed / reordered / unsupported remote steps persist completed
steps + receipt + revision so retry/reconcile converges without duplicate
issues/comments/relations and never rolls back local chart state.

### Locator re-entry (`flowctl chart locate`)

Resolves canonical chart/D-ID, stored identifier, or stored supported provider
URL **strictly** through the local provenance ledger:

- Normalize scheme/host case and provider-approved cosmetic suffixes
- Reject credential-bearing, wrong-host/project, ambiguous, unrecorded,
 stale-parent, and conflicting selectors
- Structured failures with codes such as `unresolved_locator`, `stale_id`,
 `unsupported_capability`; **zero mutation**
- No network search, no redirect following, no title inference
- Parent URL -> chart; open decision URL -> that D-ID; resolved/superseded
 decision URL -> history + replacement/frontier metadata (never silently
 different work)

## Result envelope

Success:

```json
{"success": true, "data": {}, "degraded": null, "probe": null}
```

Failure:

```json
{"success": false, "class": "conflict", "error": "redacted diagnostic", "retryable": false, "details": {}}
```

The failure class enum is `inactive`, `unresolved`, `stale_id`, `auth`,
`rate_limited`, `transport`, `not_found`, `capability`, `conflict`,
`invalid_input`, and `external_action_required`. Credentials and provider
secrets are redacted recursively from messages and details.

## Safety invariants

- Provider credentials are attached by the executor, never an adapter.
- Presigned attachment requests use anonymous credential policy.
- Automatic retries are limited to classified, idempotent requests.
- Writes validate parent identity before mutation.
- Capabilities come from `tracker.resolved`, with explicit degradation.
- Tracker bodies normalize to Markdown before reconciliation.
- Flow-owned dependency marker blocks are excluded from body divergence.
