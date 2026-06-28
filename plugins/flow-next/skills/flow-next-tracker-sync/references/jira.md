# Jira adapter — transport via the Jira REST API + token (single rung, no-op floor)

The Jira implementation of the nine-method transport interface
([adapter-interface.md](adapter-interface.md)) — the original six core methods
(`fetchIssue` / `writeIssue` / `listComments` / `postComment` / `readStatus` /
`setStatus`), the enumeration method (`listOpenIssues`, fn-68.2), and the
dependency-projection pair (`listIssueRelations` / `setIssueRelation`, fn-64.4).
This file (fn-70.2) establishes the **transport + six core + auth + identity + the
make-pr PR remote-link**; the **ADF body translation, the transitions/status model
(incl. the fn-66 terminal gate), the relation pair, and `listOpenIssues`** are
fn-70.3 — each is pointed at the boundary below, never half-built here.

Jira mirrors the **GitHub adapter's shape** ([github.md](github.md)), not the
Linear MCP-or-token ladder: Jira has **one** transport (the REST API driven over
`curl` with a token), so there is no multi-rung detection — only a **single REST
rung plus the terminal no-op**. It reuses the fn-52.4/.5 reconcile core
**unchanged** — proving the reconciliation is transport-blind (the R13 guarantee):
a transport bug stays in this file; a merge bug stays in reconcile.

| Rung | Transport | Use when | Notes |
|------|-----------|----------|-------|
| 1 | **Jira REST API** (`curl`, token from env) | a credential for the persisted `authScheme` is reachable (presence check, see below) | the only Jira transport; Cloud `/rest/api/3` (basic `email:API_TOKEN`) or DC/Server `/rest/api/2` (Bearer PAT) |
| 2 (terminal) | **no-op + receipt note** | no credential reachable for the persisted scheme | the bridge is configured but no Jira transport is reachable this run |

The chosen rung is recorded on every receipt:
`sync receipt … --transport rest|none` (the `rest` token is shared with GitLab's
raw-REST rung — it is the "raw HTTP, token from env" transport class) — plus, on a
lifecycle run, the touchpoint it served: `${EVENT:+--event "$EVENT"}` (`$EVENT` is
set in steps.md Phase 0; empty on manual runs, so the flag is omitted). The
agentic reconciliation (fn-52.4 body merge, fn-52.5 status/comments) is **identical
regardless of tracker** — that is the R13 guarantee.

> **Live-verified 2026-06-28.** The auth, create/fetch/comment, identity, and
> remote-link calls below were smoke-tested against a real Cloud site
> (`*.atlassian.net`, team-managed project, admin token, project deleted after) —
> see `flow-smoke/out/FINDINGS-jira.md`. Confirmed working: Cloud basic auth over
> `/rest/api/3`; `POST /issue` with an ADF description + labels (colon labels like
> `flow:<id>` accepted); `GET /issue/{key}`; `GET`/`POST /issue/{key}/comment` (ADF);
> `POST /issue/{key}/remotelink` (HTTP 201). **DC/Server deltas are verify-at-build**
> (no DC instance was available) — the `/rest/api/2` paths below are implemented now
> from the Atlassian Data Center REST docs and branch on the persisted `apiVersion`;
> a build-time DC pass confirms the body-shape deltas.

## Why REST + token, and not an Atlassian MCP (decision — recorded so a future spec need not re-research)

Unlike Linear (a first-class MCP rung **plus** a GraphQL rung), Jira ships **one**
rung: the REST API. The Atlassian MCP was **evaluated and deliberately not wired**.
The evidence, so this is not re-litigated:

- **The official Atlassian Remote MCP is read-mostly.** Its issue tools center on
  *search / read / summarize*; it does **not** expose the write surface tracker-sync
  needs — issue **transitions** (the fn-66 status model goes through the transitions
  API, fn-70.3), issue **links** (the fn-64 relation pair), or **remote links** (the
  make-pr PR link). A read-only transport cannot implement the write half of the
  nine-method interface, so it could at best be a partial, asymmetric rung — exactly
  the "grudging fallback" the ladder model forbids.
- **Community/third-party Jira MCP servers are a thin wrapper over the same REST API
  + the same token.** They add a second moving part (an MCP server to register and
  keep current) and a tool-name surface that **drifts** (the breadcrumb-pin problem
  the Linear MCP rung carries) **without adding any capability** the direct REST path
  lacks — they call `/rest/api/{3|2}` underneath with the user's `JIRA_API_TOKEN` /
  `JIRA_PAT`. Wiring one would be redundant indirection.
- **Enterprise teams (the audience) report Atlassian-MCP limitations and run the
  token path in CI/Ralph anyway.** The REST + token rung is the always-works floor
  that runs headlessly in their environments; an MCP rung would not be reachable
  there. (Audience copy is always **"enterprise teams"** — never the internal
  shorthand for portfolio companies.)

**Conclusion:** Jira is REST-only by design. There is **no MCP probe** in the
discovery ceremony for Jira (steps.md Phase 1) and **no MCP rung** here — the
single REST rung + the no-op floor is the whole transport. If a future Atlassian MCP
gains the transition/link/remote-link write surface, revisit this; until then the
direct REST path is strictly superior (fewer moving parts, no tool-name drift,
headless-native).

## Transport resolution — decided once at the ceremony, persisted; runtime is a presence check

The deployment shape (Cloud vs DC/Server) is **detected once at the discovery
ceremony** (steps.md Phase 1) and **persisted** — runtime **never re-infers** it.
This is the persisted-config discipline (memory:
`ceremony-validation-must-read-persisted`): the persist exists precisely so a later
use does not re-race env.

Persisted config keys (written by the ceremony, fn-70.1):

| Key | Meaning |
|---|---|
| `tracker.perTracker.baseUrl` | the site base, e.g. `https://acme.atlassian.net` (Cloud) or `https://jira.acme.com` (DC/Server). **`JIRA_BASE_URL` env overrides** the persisted value (the persisted value is the default, never inert). |
| `tracker.perTracker.projectKey` | the project key (the `listOpenIssues` JQL scope, fn-70.3) |
| `tracker.perTracker.authScheme` | `cloud-basic` (Cloud HTTP-basic `email:API_TOKEN`) \| `bearer-pat` (DC/Server Bearer PAT) — **runtime reads only this**, never re-probes which env var is set |
| `tracker.perTracker.apiVersion` | `3` (Cloud, `/rest/api/3`, ADF) \| `2` (DC/Server, `/rest/api/2`) — the REST endpoint family the adapter branches on |
| `tracker.perTracker.sslVerify` | optional; `false` opts out of TLS verification for a self-hosted cert (`curl -k`). Default `true`. Also honored as the env override `JIRA_SSL_VERIFY=false`. |

**Runtime resolution (the SAME order the ceremony validation snippet mirrors —
steps.md Phase 1 step 5):**

```bash
# baseUrl: env overrides the persisted default.
JIRA_BASE=${JIRA_BASE_URL:-$($FLOWCTL config get tracker.perTracker.baseUrl --json | jq -r '.value // empty')}
PROJ_KEY=$($FLOWCTL config get tracker.perTracker.projectKey --json | jq -r '.value // empty')
AUTH_SCHEME=$($FLOWCTL config get tracker.perTracker.authScheme --json | jq -r '.value // empty')
APIV=$($FLOWCTL config get tracker.perTracker.apiVersion --json | jq -r '.value // "3"')
SSL_VERIFY=$($FLOWCTL config get tracker.perTracker.sslVerify --json | jq -r '.value // true')

# Build the auth ARGS by the PERSISTED authScheme — NEVER by probing which env var
# happens to be set (that would re-race a decided value). Credentials are read from
# env EACH RUN and never stored in flow state.
CRED_OK=0
case "$AUTH_SCHEME" in
  cloud-basic)  # Jira Cloud: HTTP basic email:API_TOKEN over /rest/api/3
    [ -n "${JIRA_EMAIL:-}" ] && [ -n "${JIRA_API_TOKEN:-}" ] \
      && { JAUTH=(-u "$JIRA_EMAIL:$JIRA_API_TOKEN"); CRED_OK=1; } ;;
  bearer-pat)   # Jira DC/Server: Authorization: Bearer <PAT> over /rest/api/2
    [ -n "${JIRA_PAT:-}" ] \
      && { JAUTH=(-H "Authorization: Bearer $JIRA_PAT"); CRED_OK=1; } ;;
esac

# Self-hosted TLS opt-out (DC/Server private CA): persisted sslVerify=false OR env.
{ [ "$SSL_VERIFY" = false ] || [ "${JIRA_SSL_VERIFY:-}" = false ]; } && JK=(-k) || JK=()

# Rung selection — a cheap CREDENTIAL-PRESENCE check, never a support-probe.
if [ "$CRED_OK" = 1 ] && [ -n "$JIRA_BASE" ]; then TRANSPORT=rest; else TRANSPORT=none; fi
```

- **The rung is chosen by a presence check, not a live API probe** — same as the
  GitHub adapter takes `gh auth status` exit 0 as the signal and does not round-trip
  the API to decide the rung. A missing credential ⇒ the no-op rung (never a crash,
  never an interactive login prompt).
- **Credentials are read from env each run and never written to flow state.** Only
  the deployment *shape* (baseUrl/authScheme/apiVersion/sslVerify) is persisted — the
  secret itself stays in the environment.

## No-op rung (terminal) — never crash

When `TRANSPORT=none`, the configured bridge cannot reach Jira this run. Every one
of the nine interface methods becomes a documented no-op (same fail-soft contract as
the GitHub terminal rung and fn-51's manual rung) — including `listOpenIssues`
(returns `[]`, fn-68.2 / fn-70.3) and the relation pair (fn-64.4 / fn-70.3):

- `fetchIssue` / `listComments` / `readStatus` / `listIssueRelations` → return
  nothing actionable ("no remote view available this run"); the spec's flow-side
  state is left untouched and the merge base is NOT advanced.
- `writeIssue` / `postComment` / `setStatus` / `setIssueRelation` → perform no
  remote write.
- The run emits `sync receipt … --status noop --transport none ${EVENT:+--event "$EVENT"}
  --note "no Jira transport reachable (no JIRA_EMAIL+JIRA_API_TOKEN / JIRA_PAT for the persisted authScheme, or baseUrl unset)"`.
- `lastSyncedAt` is never advanced on a no-op (no real reconciliation happened).

## Auth — two distinct schemes, labelled unambiguously (a Cloud user has no "PAT")

Jira has **two deployment families with two different auth schemes**. The ceremony
detects and persists which one applies (`authScheme`); this adapter branches on the
persisted value. **Label them so a Cloud user is never told to create a non-existent
"PAT", and a DC/Server user is never sent to the Cloud token page.**

| Deployment | `authScheme` | `apiVersion` | Credential (env) | `curl` auth | Endpoint family |
|---|---|---|---|---|---|
| **Jira Cloud** (`*.atlassian.net`) | `cloud-basic` | `3` | `JIRA_EMAIL` + `JIRA_API_TOKEN` (an **API token** from id.atlassian.com — **not** a PAT) | `-u "$JIRA_EMAIL:$JIRA_API_TOKEN"` (HTTP basic) | `/rest/api/3` (ADF bodies) |
| **Jira Data Center / Server** (self-hosted) | `bearer-pat` | `2` | `JIRA_PAT` (a **Personal Access Token**, minted in the user's Jira profile) | `-H "Authorization: Bearer $JIRA_PAT"` | `/rest/api/2` |

- **Cloud basic auth is `email:API_TOKEN`, NOT password.** The token is the
  long-lived API token from `id.atlassian.com`; the email is the Atlassian-account
  email. Basic-auth-with-password is deprecated on Cloud — only the API token works.
  (Confirmed working live 2026-06-28.)
- **DC/Server uses a Bearer PAT** (`Authorization: Bearer <token>`), the Personal
  Access Token feature in self-hosted Jira (8.14+). There is **no `email:` pairing**
  on this scheme.
- **Self-hosted TLS:** a DC/Server instance behind a private CA may present a cert
  `curl` won't verify. Opt out per the persisted `sslVerify=false` (or env
  `JIRA_SSL_VERIFY=false`) → `curl -k`. **Opt-in only** — verification stays on by
  default; never silently disable it.
- **Never store credentials in flow state.** The env vars are read each run; only
  the non-secret deployment shape is persisted.

> **Endpoint family — the one branch that matters.** Everywhere below, `$APIV` is
> the persisted `apiVersion` (`3` Cloud / `2` DC/Server) and every path is
> `"$JIRA_BASE/rest/api/$APIV/…"`. The two families share the **same path grammar**
> for the six core methods (`/issue`, `/issue/{idOrKey}`, `/issue/{idOrKey}/comment`,
> `/issue/{idOrKey}/remotelink`); the principal delta is the **body format** —
> `/rest/api/3` bodies (description + comment) are **ADF**, `/rest/api/2` accepts
> wiki-markup/plain text. The ADF translation itself is fn-70.3 (§ ADF boundary
> below); for the six core, branch on `$APIV` only for the body shape.

## Identity — durable `tracker.id` is the immutable issue `id`, NOT the display key

Jira exposes **two** identifiers per issue; getting these straight is load-bearing:

- **`id`** — the **immutable numeric issue id** (a stable string like `"10042"`),
  assigned at create and never reused or changed. This is the **durable
  `tracker.id`** — the dedupe key stored via `sync set-tracker-id`. It survives a
  project-key rename or an issue move.
- **`key`** — the **display key** `PROJ-123` (project key + sequence). This is the
  normalized **`identifier`** surfaced to humans. It is **mutable**: moving an issue
  to another project, or renaming the project key, changes the `key` but **not** the
  `id`. Never store the `key` as the durable id.

**The link flow accepts a `key`, resolves it to the `id`, then persists the `id`:**

```bash
# A human links by the display key (that is what they see on the board).
# Resolve key → immutable id BEFORE persisting (one GET):
RESP=$(curl -sS "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
         "$JIRA_BASE/rest/api/$APIV/issue/PROJ-123?fields=summary")
ISSUE_ID=$(printf '%s' "$RESP" | jq -r '.id')      # immutable durable id, e.g. "10042"
ISSUE_KEY=$(printf '%s' "$RESP" | jq -r '.key')    # display identifier "PROJ-123"
ISSUE_URL="$JIRA_BASE/browse/$ISSUE_KEY"           # the browse URL

# Store the IMMUTABLE id as the durable tracker-id; the key is the display identifier.
$FLOWCTL sync set-tracker-id "<spec-id>" "$ISSUE_ID" --identifier "$ISSUE_KEY" --url "$ISSUE_URL"
```

- **A Jira issue key `PROJ-123` is an alpha-prefixed `KEY-N`**, so Jira grabs go
  **tracker-first like Linear** (steps.md): `spec create --tracker-first
  --tracker-identifier PROJ-123` mints a clean `proj-123-slug` canonical id, and bare
  `proj-123` / `proj-123.M` resolve like `wor-17`. Both entry flows work (tracker-first
  AND flow-first). Distinct from GitHub/GitLab (flow-first only — their keys don't
  slugify into a canonical id).
- **Refresh the `identifier` from every fetch response.** Because the `key` is
  mutable, each `fetchIssue` re-reads `.key` and surfaces the current display key —
  the durable `id` in storage is the join key; the displayed `identifier` follows the
  live `key`.
- **Back-reference:** the linked issue carries a `flow:<spec-id>` **label** (colon
  labels are accepted on Jira — confirmed live) plus a body anchor, so the issue
  points back at the spec. Linkage is decided authoritatively by the **local sync
  state** (the recorded linked tracker-id), not by the label's presence — the label
  is a corroborating hint only (same rule as the other adapters).
- **Runtime prefers the durable `id` over the mutable key** in every per-issue path
  below: paths take Jira's `{issueIdOrKey}` placeholder, and we pass the stored
  **`id`** (immune to a key rename), not the `key`.

## Normalized mapping — the firewall

The Jira REST JSON wire shape maps **to/from** the normalized structs in
[adapter-interface.md](adapter-interface.md) (`issue` / `comment` /
`status {raw, normalized}`) **at the adapter boundary**. Reconcile (fn-52.4/.5) only
ever sees the normalized form — a transport bug stays in this file; a merge bug stays
in reconcile.

| normalized `issue` field | Jira source (`GET /issue/{idOrKey}` JSON) | Notes |
|---|---|---|
| `id` | `id` (immutable issue id, e.g. `"10042"`) | **durable dedupe key** — stored via `sync set-tracker-id`. Never the `key`. |
| `identifier` | `key` (e.g. `PROJ-123`) | display only; **mutable** — refreshed from each fetch. |
| `title` | `fields.summary` | |
| `body` | `fields.description` | ADF on `/rest/api/3` → normalized markdown via the ADF translation (**fn-70.3**); on `/rest/api/2` it is wiki/plain text. Until fn-70.3 lands the translation, the body is carried as the raw ADF/text round-trip (see § ADF boundary). |
| `status.raw` | `fields.status.name` (+ `fields.status.statusCategory.key`) | the literal Jira status; the **status model + normalization is fn-70.3** (terminal detection keys off `statusCategory.key` ∈ `new`/`indeterminate`/`done`, NOT the project-specific name). |
| `status.normalized` | the fn-70.3 status map | deferred — see § Status boundary. |
| `priority` | `fields.priority.name` | folded, never auto-changed (R7). |
| `labels` | `fields.labels[]` | includes the `flow:<spec-id>` back-reference label. |
| `url` | `"$JIRA_BASE/browse/" + key` | the browse URL (Jira's `self` is the API URL, not the human one). |
| `updatedAt` | `fields.updated` | drives staleness + echo-suppression. |

`tracker`/`type` on the struct are set to `"jira"` / `"issue"`.

## The core interface methods over the Jira REST API

The original **six** core methods. Mapping wire ↔ normalized happens here, at the
adapter boundary; reconcile never sees a Jira JSON shape. Every path is
`"$JIRA_BASE/rest/api/$APIV/…"` with `"${JAUTH[@]}"` (the persisted-scheme auth) and
`"${JK[@]}"` (the TLS opt-out). The **per-issue path placeholder is `{issueIdOrKey}`
— pass the stored immutable `id`**, not the mutable key.

### `fetchIssue(trackerId)` → normalized `issue` | not-found

```bash
# trackerId is the stored immutable id. Request only the fields the firewall maps.
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
  "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID?fields=summary,description,status,priority,labels,updated"
```

- Map per the firewall table above. `fields.status` → `status` (the normalization is
  fn-70.3; for now carry `status.raw` = `fields.status.name`).
- **not-found:** a deleted/moved/permission-lost issue returns **HTTP 404** (Jira:
  `{"errorMessages":["Issue does not exist..."]}`). `fetchIssue` returns
  `not-found` — **never raises out of the adapter**. The skeleton then emits an
  `errored` receipt + prompts/queues unlink (see the error contract below).

### `writeIssue(issue)` → `{id, identifier, url}` (upsert)

Upsert by presence of `issue.id` (interface rule): no id ⇒ **create** (`POST
/issue`); id present ⇒ **update** (`PUT /issue/{issueIdOrKey}`).

```bash
# CREATE (no issue.id). Body is JSON; the description is ADF on /rest/api/3
# (the ADF doc is built by the fn-70.3 translation — § ADF boundary). issuetype by
# name ("Task") works (confirmed live). Colon labels (flow:<id>) are accepted.
#   projectKey = tracker.perTracker.projectKey
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -X POST "$JIRA_BASE/rest/api/$APIV/issue" \
  --data @<(jq -n --arg pk "$PROJ_KEY" --arg sum "$TITLE" --arg lbl "flow:$FLOW_ID" \
              --argjson desc "$ADF_DESCRIPTION" '
              { fields: { project: {key:$pk}, issuetype: {name:"Task"},
                          summary: $sum, description: $desc, labels: [$lbl] } }')
# The 201 response carries {id, key, self}. Build the browse url from key:
#   id=.id  identifier=.key  url="$JIRA_BASE/browse/"+.key

# UPDATE (issue.id present) — PUT replaces only the supplied fields (HTTP 204, no body).
# PRESERVE the flow-owned <!-- flow:deps -->…<!-- /flow:deps --> region on write
# (fn-64 / fn-70.3): the rendered spec body never contains the dep block, so a raw
# description replace would WIPE it. Read the current description, carry its fenced
# block forward into the rendered body, THEN PUT. (Implemented in fn-70.3 alongside
# the ADF splice — until then writeIssue updates summary/labels and the description
# round-trips the raw form. § Relation boundary.)
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" \
  -X PUT "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID" \
  --data @<(jq -n --arg sum "$TITLE" --argjson desc "$ADF_DESCRIPTION_WITH_DEPS" \
              '{ fields: { summary: $sum, description: $desc } }')
```

- **Bodies go in the JSON request body, never on a shell flag.** Build the JSON with
  `jq` (it handles escaping of the markdown/ADF) and pass it via `--data @-` / a
  process substitution — the Jira analog of GitHub's "`--body-file -`, never raw
  `--body`" and Linear's "pass bodies as GraphQL variables" rule. Same failure mode
  (shell quoting mangles the round-trip), same fix.
- **`POST /issue` returns `{id, key, self}`** (HTTP 201) — capture the immutable `id`
  (durable), the `key` (identifier), and build the browse `url` as
  `"$JIRA_BASE/browse/$key"`. Return `{ id, identifier (key), url }`.
- **`PUT /issue/{idOrKey}` returns HTTP 204** (no body) on success — do **not** parse
  a response body; re-`fetchIssue` if the caller needs the post-write struct.
- **Write the flow back-reference on create:** the `flow:<spec-id>` label (and a body
  anchor). Jira accepts colon labels and auto-creates unknown labels on write (no
  pre-create step, unlike the GitHub `status:`/`flow:` labels) — confirmed live.
- **ADF boundary (fn-70.3):** `$ADF_DESCRIPTION` is the markdown→ADF translation
  output. On `/rest/api/3` the description MUST be an ADF doc
  (`{"type":"doc","version":1,"content":[…]}`, confirmed to round-trip exactly); on
  `/rest/api/2` it is wiki/plain text. The splice algorithm (markdown ↔ ADF,
  unknown-node preservation, the deps-block carry-forward) lives in **fn-70.3** — this
  file references the boundary; it does not implement the translator.

### `listComments(trackerId)` → normalized `comment[]`

```bash
curl -sS "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
  "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID/comment"
# → { comments: [ { id, author:{accountId,accountType,displayName}, body, created, updated }, … ], total, … }
```

- **Jira comment ids are stable** (the numeric `comment.id`) — the dedup key, same
  property the GitHub/Linear comment ids carry.
- Map each: `author.displayName` → `author`; `body` (ADF on v3 → markdown via the
  fn-70.3 translation; on v2 plain/wiki) → `body`; `created` → `createdAt`.
- **`author.accountType` → `authorAuthority`** (fn-68 R15 security — populate it here,
  the producer). The enum is fixed (`writer|outsider|bot|unknown` — **no new value**,
  fn-68 contract):
  - `accountType == "app"` ⇒ **`bot`** (an Atlassian app / Connect add-on / automation).
  - `accountType == "customer"` ⇒ **`outsider`** (a JSM customer-portal account).
  - `accountType == "atlassian"` (a real Jira user) ⇒ **NOT auto-`writer`.** The
    comment author object carries no inline role, so being an internal user is not by
    itself proof of write authority. Gate `writer` on a **project-role / group
    membership check** (or an explicit `tracker.answerAuthors` allowlist); if that
    cannot be resolved this run, fall **`unknown` / fail-closed** — the answer valve
    treats `unknown` as NOT authorized. Never collapse `atlassian` → `writer`
    silently.
  - absent / unparsed `accountType` ⇒ **`unknown`** (fail closed).
- **Detect the flow-owned marker set** in the comment body → set `comment.marker`. The
  set is **closed** (fn-68 R15, [adapter-interface.md](adapter-interface.md) §
  `comment` marker-vocabulary table): `flow-next:sync`→`flow-evt:<event>`,
  `flow-next:question`→`flow-evt:question`, rolling `flow-next:status`→`flow-evt:status`
  (all flow-owned, skip Sync-Log). `flow-next:answer` is the one human-authored marker
  — `marker` stays **`null`**, but surface its `id` (the answer round-trip claims it by
  `id` before the generic Sync-Log append). Genuine tracker-side comments get
  `marker:null` and pull into the spec sync log.
- **Threading / `parentId`.** Jira issue comments are **flat** (no native
  parent/reply link on the issue-comment endpoint), so — like GitHub — `parentId` is
  `null` and the **answer is matched to its question by the body `id` marker**
  (threading-blind), not by thread. The `<!-- flow-next:answer id=<hash> -->` marker
  is the load-bearing match (adapter-interface.md § `comment`; steps.md Phase 7).
- The markers live inside the ADF/text body; the fn-70.3 ADF translation surfaces the
  body as markdown so the marker scan runs on normalized text (the marker comments are
  HTML-comment lines flow itself wrote, so they survive the ADF round-trip).

### `postComment(trackerId, body)` → normalized `comment`

```bash
# body carries the flow-evt:<event> marker line (echo suppression + dedup). On v3 the
# comment body is ADF (fn-70.3 translation); on v2 plain/wiki.
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -X POST "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID/comment" \
  --data @<(jq -n --argjson b "$ADF_COMMENT_BODY" '{ body: $b }')
# → 201 { id, author, body, created, … } — map to the returned normalized comment.
```

- `$ADF_COMMENT_BODY` carries the `flow-evt:<event>` marker line (echo suppression +
  dedup, per [comments-sync.md](comments-sync.md)).
- **`POST …/comment` returns the created comment** (HTTP 201) with its stable `id` —
  map it to the returned normalized `comment` directly (no re-list needed, unlike
  `gh issue comment`).
- Build the JSON body with `jq` — never interpolate the markdown/ADF into a shell
  string.

### `readStatus(trackerId)` → normalized `status`

Derived from the `fetchIssue` `fields.status` (`name` + `statusCategory.key`) — no
separate call (same as the GitHub adapter deriving status from `state`+`stateReason`).
**The normalization map (raw Jira status → flow vocabulary) and the fn-66 terminal
gate are fn-70.3** (§ Status boundary). For the six-core scope, `readStatus` surfaces
`status.raw = fields.status.name` and defers the `normalized` mapping to fn-70.3.

### `setStatus(trackerId, status)` → ok | errored — **deferred to fn-70.3**

Jira forbids a direct status write: you cannot `PUT fields.status`. A status change
goes through the **transitions API** (`GET /issue/{idOrKey}/transitions` →
`POST /issue/{idOrKey}/transitions {transition:{id}}`), resolving the legal transition
id from the issue's *current* status. That model — plus the fn-66 terminal invariant
(locally-`done` → In Review until a `MERGED` PR, terminal Done gated on merge
evidence) and the "illegal/unreachable transition ⇒ defer + receipt, never force"
rule — is **fn-70.3** ([→ § Status / transitions boundary]). It is intentionally NOT
stubbed here: a half-implemented direct-status write would be wrong on Jira.

### `listOpenIssues` / `listIssueRelations` / `setIssueRelation` — **deferred to fn-70.3**

The enumeration method (`listOpenIssues`, fn-68.2) and the dependency-projection pair
(`listIssueRelations` / `setIssueRelation`, fn-64.4) are **fn-70.3**. Boundary notes
so the build doesn't re-research them:

- **`listOpenIssues`** filters the promoted lane by the `tracker.readyState` **Jira
  status name** via JQL. **The search endpoint is `POST /rest/api/3/search/jql`** with
  body `{jql, fields, maxResults}` — the old `GET /rest/api/3/search` returns **HTTP
  410 REMOVED** (CHANGE-2046, confirmed live 2026-06-28); pagination is **cursor-based**
  (`isLast` + `nextPageToken`), not the legacy `total`/`startAt` offset model. Escape
  the status name before interpolating into the JQL.
- **Relations** project the blocked-by edge as a Jira **issue link**: `POST
  /rest/api/3/issueLink` with `{type:{name:"Blocks"}, outwardIssue, inwardIssue}`
  (HTTP 201, confirmed live). `outwardIssue` **blocks** `inwardIssue` (`inwardIssue`
  shows "is blocked by") — so for `depends_on` the **dependency** is `outwardIssue`
  and the **current issue** is `inwardIssue`. Direction is anchored once in
  adapter-interface.md § Direction convention; read-before-write dedup + the
  never-delete-non-ours provenance (ledger) apply.

## ADF boundary (fn-70.3) — what this file does and does NOT do

Jira `/rest/api/3` issue **descriptions and comment bodies are ADF** (Atlassian
Document Format — `{"type":"doc","version":1,"content":[…]}`, confirmed to round-trip
exactly live). The **markdown ↔ ADF translation, the round-trip-safe subset, and the
unknown-node-preservation rule are fn-70.3.** This file:

- **References** the boundary (every `writeIssue` / `postComment` above takes an
  `$ADF_*` body that the fn-70.3 translator produces; every read maps ADF → markdown
  via that translator).
- **Does NOT implement** the splice algorithm. The only stub pointer `writeIssue`
  needs is "the description body is ADF on v3 / wiki-or-plain on v2, built by the
  fn-70.3 translation; preserve the `<!-- flow:deps -->` fenced region on UPDATE" —
  recorded above, not coded here.

Keeping the translator out of this task keeps the six-core transport contract
reviewable on its own; the ADF work is a self-contained fn-70.3 deliverable.

## `makePr` — link the PR to the issue as a **remote link** (in-adapter)

When the tracker is **Jira**, the spec maps to a Jira *issue* and the PR lives in a
git host (GitHub/GitLab) Jira does not natively cross-reference. Jira has **neither**
GitHub's `Refs #N` auto-linkify **nor** Linear's auto-detected Diffs attachment, and
**Smart-Commit `PROJ-123` keys are not relied on** (they need a DVCS connector that
may be absent). So the make-pr PR link projects to Jira as a **remote link** written
**in-adapter** — the In-Review-rung evidence equivalent:

```bash
# POST a remote link carrying the PR url + a title. HTTP 201 (confirmed live 2026-06-28).
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -X POST "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID/remotelink" \
  --data @<(jq -n --arg url "$PR_URL" --arg title "$PR_TITLE" \
              '{ object: { url: $url, title: $title } }')
```

- **Remote link, not a Smart-Commit key and not an auto-linkify.** The remote link is
  the durable, connector-free PR↔issue projection — it renders in the issue's "Web
  links" / remote-links panel regardless of whether a DVCS connector exists.
- **Fallback:** if the remote-link POST fails (permission, older DC build), fall back
  to a **URL comment** (`postComment` carrying the PR url + the lifecycle marker) — the
  same "comment with the PR URL" equivalence the spec allows. Never crash; emit the
  receipt.
- **DC/Server:** the `/rest/api/2/issue/{idOrKey}/remotelink` path is the v2
  equivalent — branch on `$APIV` (verify-at-build on a DC instance).
- **Gate:** bridge **active AND `tracker.type == jira`** — no separate `makePr`
  opt-in (one of the two unconditional-when-active exceptions, steps.md). This rides
  the same In-Review status push the other adapters do (the status push itself is
  fn-70.3's transitions model); the remote link is the link half and is owned here.
- No auto-linkify, no `gh`, no Linear attachment — the remote link IS the projection.

## Error contract — never crash, never corrupt state

The adapter honors the [adapter-interface.md](adapter-interface.md) contract rules.
The failure modes that MUST be non-destructive:

- **Missing / deleted / moved / 404 linked issue** — `GET /issue/{idOrKey}` returns
  **HTTP 404** (`Issue does not exist`). `fetchIssue` returns `not-found` (NEVER
  raises). The skeleton then:
  - emits `sync receipt … --status errored --transport rest ${EVENT:+--event "$EVENT"}`,
  - does **NOT** crash, does **NOT** clear state, does **NOT** advance `lastSyncedAt`
    (a failed fetch must never corrupt the merge base),
  - prompts the user to unlink (interactive) or queues an unlink decision (`sync
    defer`, Ralph) — never a silent `sync clear`.
- **Auth failure mid-run** (`JIRA_API_TOKEN` / `JIRA_PAT` expired or revoked) — Jira
  returns **HTTP 401** (and **403** for a valid-but-unauthorized token, e.g. no
  permission on the project). Treat as the **no-op rung** for that operation: `noop`
  receipt + actionable note ("Jira 401/403 — refresh JIRA_API_TOKEN / JIRA_PAT, or
  check project permission"), no state write — same as never having had a transport.
- **Rate limit** — Jira returns **HTTP 429 with a `Retry-After` header** (Cloud also
  surfaces `X-RateLimit-*` on some endpoints). **Back off and retry** (exponential,
  honor `Retry-After`) rather than failing the run — same non-destructive contract as
  the other adapters, Jira's signal.
- **TLS failure on a self-hosted instance** — a `curl` cert error (exit 60) on a
  DC/Server host means verification failed; surface the actionable note (set
  `tracker.perTracker.sslVerify=false` or `JIRA_SSL_VERIFY=false` if the private CA is
  trusted) — never silently retry with `-k`.
- **Batch sync is item-level** — one spec's `errored`/rate-limit does not abort the
  batch: that spec gets its own `errored` receipt + no state write, and the run
  continues to the next spec.
- **Echo suppression** — after a push, the resulting tracker-side body hash is
  recorded (rides on the merge-base snapshot, fn-52.4); the next pull's matching hash
  ⇒ flow's own echo ⇒ `noop`, never a phantom conflict. `fields.updated` from the Jira
  JSON helps distinguish a real Jira-side edit from an echo. Comment echo uses the
  `flow-evt:<event>` marker (above), same as the other adapters.

## Boundaries

- **This is the transport, not the merge.** The adapter maps Jira REST JSON ↔
  normalized and routes the single rung / no-op. The 3-way body merge
  ([body-merge.md](body-merge.md), fn-52.4), the status who-wins
  ([status-sync.md](status-sync.md), fn-52.5), and the comments/evidence append +
  dedup ([comments-sync.md](comments-sync.md), fn-52.5) consume the normalized structs
  and live in those tasks — **reused unchanged** here.
- **REST-only by design — no MCP rung** (the decision above). One transport + the
  no-op floor; no detect-best-available ladder.
- **This task (fn-70.2) is the transport + six core + auth + identity + PR
  remote-link.** The ADF translation, the transitions/status model (incl. the fn-66
  terminal gate), the relation pair, and `listOpenIssues` are **fn-70.3** — pointed at
  the boundary above, never half-built here.
- **No new hard dependency.** Only `curl` + `jq` (already required by the bridge); the
  terminal rung is a documented no-op. The zero-dep base install is untouched
  (STRATEGY opt-in carve-out).
- **One Jira issue per linked spec** (`tracker.perTracker.baseUrl` + `projectKey`) —
  the bridge config resolves a single site/project, mirroring the one-team Linear /
  one-repo GitHub constraint.
- **Codex mirror** (sync-codex.sh) is regenerated in fn-70.4 — keep this file
  Claude-native; no Codex-specific edits here.
