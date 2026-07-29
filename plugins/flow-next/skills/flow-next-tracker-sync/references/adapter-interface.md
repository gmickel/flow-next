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

## Normalized comment

```json
{
  "id": "provider comment id",
  "body": "plain markdown",
  "author": {"id": "provider id", "name": "display name"},
  "createdAt": "provider timestamp",
  "updatedAt": "provider timestamp",
  "parentId": "durable issue id or null"
}
```

`parentId` is included only when the provider response exposes it. Parent
identity is never inferred from a URL-shaped string.

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
| `list-open` | resolved ready lane | normalized issue list | none |
| `attach` | locator, file | attachment metadata | none |
| `attach-get` | attachment id, output path | retrieved metadata | output file only |

Pagination is exhausted inside the adapter. Consumers never receive a provider
cursor or page token.

## Lifecycle verbs

Lifecycle verbs are spec-aware. They may update the linked tracker block and
write one receipt:

- `create` creates and links an issue for an existing spec.
- `create-first` creates before a spec and writes retry-key recovery state.
- `persist-external` records an authorized MCP result.
- `status` applies the deterministic status policy.
- `relate` projects one blocked-by edge with provenance.
- `sync-body` performs write/readback and paired merge-base persistence.
- `sync` composes the event lifecycle as one unit.

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
