# Jira adapter — transport via the Jira REST API + token (single rung, no-op floor)

The Jira implementation of the nine-method transport interface
([adapter-interface.md](adapter-interface.md)) — the original six core methods
(`fetchIssue` / `writeIssue` / `listComments` / `postComment` / `readStatus` /
`setStatus`), the enumeration method (`listOpenIssues`, fn-68.2), and the
dependency-projection pair (`listIssueRelations` / `setIssueRelation`, fn-64.4).
fn-70.2 established the **transport + six core + auth + identity + the make-pr PR
remote-link**; **fn-70.3** lands the Jira-specific weight: the **Markdown↔ADF body
translation** (round-trip-safe subset + unknown-node preservation), the
**transitions-API status model** (statusMap + the `statusCategory` terminal signal +
the fn-66 terminal gate + defer-on-unreachable), the **relation pair** (`Blocks`
issue links with read-before-write dedup + defer-on-human-removal), and
**`listOpenIssues`** (Cloud `POST /search/jql` cursor + DC/Server `/rest/api/2/search`
offset). The readiness projection's Jira branch lives in
[status-sync.md](status-sync.md) (§ Readiness projection — a name-match like Linear).

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
| `tracker.perTracker.projectKey` | the project key (the `listOpenIssues` JQL scope; validated `^[A-Z][A-Z0-9]+$` before JQL interpolation — § `listOpenIssues`) |
| `tracker.perTracker.statusMap` | normalized status → Jira target `{"id":…}\|{"name":…}` (id preferred); the FULL normalized set — § Status / transitions. `tracker.readyState` (the promoted-lane Jira **status name**) is used RAW, NOT through this map. |
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
(returns `[]`, fn-68.2) and the relation pair (fn-64.4):

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
> wiki-markup/plain text. The ADF translation is § ADF translation below; for the
> six core, branch on `$APIV` only for the body shape.

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
| `body` | `fields.description` | ADF on `/rest/api/3` → normalized markdown via the ADF translation (§ ADF translation); on `/rest/api/2` it is wiki/plain text. |
| `status.raw` | `fields.status.name` (+ `fields.status.statusCategory.key`) | the literal Jira status; the **status model + normalization** is § Status / transitions (terminal detection keys off `statusCategory.key == "done"`, NOT the project-specific name). |
| `status.normalized` | the `statusMap` reverse-map (§ Status / transitions) | the reverse of the write map; `statusCategory.key` fallback, else unmapped → defer. |
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

- Map per the firewall table above. `fields.status` → `status` (the normalization —
  the `statusMap` reverse-map + the `statusCategory` terminal signal — is § Status /
  transitions; `status.raw` = `fields.status.name`).
- **not-found:** a deleted/moved/permission-lost issue returns **HTTP 404** (Jira:
  `{"errorMessages":["Issue does not exist..."]}`). `fetchIssue` returns
  `not-found` — **never raises out of the adapter**. The skeleton then emits an
  `errored` receipt + prompts/queues unlink (see the error contract below).

### `writeIssue(issue)` → `{id, identifier, url}` (upsert)

Upsert by presence of `issue.id` (interface rule): no id ⇒ **create** (`POST
/issue`); id present ⇒ **update** (`PUT /issue/{issueIdOrKey}`).

```bash
# CREATE (no issue.id). Body is JSON. The DESCRIPTION FIELD branches on apiVersion:
# v3 (Cloud) = an ADF DOC — `--argjson desc` (a JSON object built by markdown→ADF, § ADF
#   translation; a create has no current ADF, so it builds from the supported subset only);
# v2 (DC/Server) = wiki/plain TEXT — `--arg desc` (a STRING).
# NEVER --argjson a v2 string: jq rejects it as invalid JSON, and an ADF object is wrong
# on /rest/api/2. Colon labels accepted.  projectKey = tracker.perTracker.projectKey
# ISSUE TYPE — DISCOVER it, never hard-code "Task" (a project's issue-type scheme may not
# include "Task"; the create would 400). Prefer a configured tracker.perTracker.issueType,
# else read the project's createable types and pick "Task" if present, else the first
# STANDARD (non-subtask) type. (createmeta shape differs Cloud v3 vs DC v2 — verify-at-build.)
ITYPE="${CFG_ISSUE_TYPE:-}"   # tracker.perTracker.issueType, if the user pinned one
if [ -z "$ITYPE" ]; then
  ITYPE=$(curl -sS "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
    "$JIRA_BASE/rest/api/$APIV/issue/createmeta/$PROJ_KEY/issuetypes" \
    | jq -r '(.issueTypes // .values // []) | map(select(.subtask|not))
             | ((map(select(.name=="Task"))[0]) // .[0] // {}).name // empty')
  [ -z "$ITYPE" ] && ITYPE="Task"   # last-resort default if discovery returned nothing
fi
if [ "$APIV" = 3 ]; then DESC_ARG=(--argjson desc "$ADF_DESCRIPTION"); else DESC_ARG=(--arg desc "$TEXT_DESCRIPTION"); fi
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -X POST "$JIRA_BASE/rest/api/$APIV/issue" \
  --data @<(jq -n --arg pk "$PROJ_KEY" --arg sum "$TITLE" --arg lbl "flow:$FLOW_ID" --arg it "$ITYPE" \
              "${DESC_ARG[@]}" '
              { fields: { project: {key:$pk}, issuetype: {name:$it},
                          summary: $sum, description: $desc, labels: [$lbl] } }')
# The 201 response carries {id, key, self}. Build the browse url from key:
#   id=.id  identifier=.key  url="$JIRA_BASE/browse/"+.key

# UPDATE (issue.id present) — PUT replaces only the supplied fields (HTTP 204, no body).
# PRESERVE human-authored ADF the spec body doesn't model: the fetch-current-first ADF
# write path (§ ADF translation — Write direction) re-reads the current description and
# carries any unknown/unsupported ADF nodes (panels, tables, media a Jira editor added)
# forward verbatim, splicing the updated spec prose ONLY into the supported-subset
# regions — a raw regenerate-from-markdown would WIPE them. $ADF_DESCRIPTION is that
# spliced doc. (Jira has NO <!-- flow:deps --> body block — dependency edges are NATIVE
# issue links, § Relation transport — so there is no dep block to carry, unlike the
# GitHub fenced fallback / GitLab degraded tier.)
# Same apiVersion body branch as CREATE: v3 ADF doc (--argjson) / v2 plain text (--arg).
# On v2 the ADF fetch-current-splice does not apply — the body is a plain-text round-trip,
# so $TEXT_DESCRIPTION is the rendered prose; DESC_ARG carries the right shape either way.
if [ "$APIV" = 3 ]; then DESC_ARG=(--argjson desc "$ADF_DESCRIPTION"); else DESC_ARG=(--arg desc "$TEXT_DESCRIPTION"); fi
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" \
  -X PUT "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID" \
  --data @<(jq -n --arg sum "$TITLE" "${DESC_ARG[@]}" \
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
- **ADF body (§ ADF translation):** `$ADF_DESCRIPTION` is the markdown→ADF translation
  output. On `/rest/api/3` the description MUST be an ADF doc
  (`{"type":"doc","version":1,"content":[…]}`, confirmed to round-trip exactly); on
  `/rest/api/2` it is wiki/plain text. The splice algorithm (markdown ↔ ADF,
  unknown-node preservation) is § ADF translation below.

### `listComments(trackerId)` → normalized `comment[]`

```bash
# PageOfComments is PAGINATED (startAt / maxResults / total) — read ALL pages or an issue
# with many comments is silently truncated to the first page. OFFSET pagination (NOT the
# v3 /search/jql cursor — different endpoint): loop until startAt >= total.
CFILE=$(mktemp "${TMPDIR:-/tmp}/jira-comments.XXXXXX")   # UNIQUE per run — concurrent reconciles must NOT share a fixed path
START=0; PER=100
while :; do
  PAGE=$(curl -sS "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
    "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID/comment?startAt=$START&maxResults=$PER")
  # GUARD: a non-JSON / error body must NOT read as total=0 (that would silently truncate).
  # Validate JSON with `jq empty` (do NOT use `jq -e .total` — `-e` exits nonzero on a
  # FALSY result, so a valid empty issue with `total: 0` would be mis-flagged as an error).
  printf '%s' "$PAGE" | jq empty 2>/dev/null \
    || { rm -f "$CFILE"; sync_receipt errored "listComments: non-JSON page at startAt=$START"; return; }
  TOTAL=$(printf '%s' "$PAGE" | jq -r '.total // -1')      # -1 sentinel = .total field absent (≠ a real 0)
  [ "$TOTAL" -lt 0 ] && { rm -f "$CFILE"; sync_receipt errored "listComments: page missing .total at startAt=$START"; return; }
  printf '%s' "$PAGE" | jq -c '.comments[]?' >> "$CFILE"   # `[]?` tolerates an absent comments array
  # total: 0 (empty issue) → falls straight through: no comments appended, START(=PER) ≥ 0 → break.
  START=$((START + PER)); [ "$START" -ge "$TOTAL" ] && break
done
# each page → { comments: [ { id, author:{accountId,accountType,displayName}, body, created, updated }, … ], total, startAt, maxResults }
# $CFILE now holds EVERY comment (one JSON per line); map each per the firewall below, then `rm -f "$CFILE"`.
```

- **Jira comment ids are stable** (the numeric `comment.id`) — the dedup key, same
  property the GitHub/Linear comment ids carry.
- Map each: `author.displayName` → `author`; `body` (ADF on v3 → markdown via the
  § ADF translation read direction; on v2 plain/wiki) → `body`; `created` → `createdAt`.
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
- The markers live inside the ADF/text body; the § ADF translation read direction
  surfaces the body as markdown so the marker scan runs on normalized text (the marker
  comments are HTML-comment lines flow itself wrote, so they survive the ADF round-trip
  as plain text nodes — § ADF translation, the flow-marker note).

### `postComment(trackerId, body)` → normalized `comment`

```bash
# body carries the flow-evt:<event> marker line (echo suppression + dedup). Branch the
# comment body by apiVersion exactly like writeIssue: v3 = ADF doc (--argjson b, a JSON
# object); v2 (DC/Server) = plain/wiki TEXT (--arg b, a STRING). Never --argjson a v2 string.
if [ "$APIV" = 3 ]; then CBODY_ARG=(--argjson b "$ADF_COMMENT_BODY"); else CBODY_ARG=(--arg b "$TEXT_COMMENT_BODY"); fi
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -X POST "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID/comment" \
  --data @<(jq -n "${CBODY_ARG[@]}" '{ body: $b }')
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

Derived from the `fetchIssue` `fields.status` (`name` + `id` + `statusCategory.key`) —
no separate call (same as the GitHub adapter deriving status from `state`+`stateReason`).
The full **status model** — the `statusMap` reverse-map, the `statusCategory` terminal
signal, and the fn-66 terminal gate — is **§ Status / transitions** below;
`status.raw = fields.status.name` and `status.normalized` is the reverse-map result.

### `setStatus(trackerId, status)` → ok | errored

Jira forbids a direct status write (`PUT fields.status` is rejected) — a status
change goes through the **transitions API**. The full model (transition resolution,
`statusMap`, the fn-66 terminal invariant, defer-on-unreachable) is **§ Status /
transitions** below.

### `listOpenIssues` / `listIssueRelations` / `setIssueRelation`

The enumeration method (`listOpenIssues`, fn-68.2) is **§ `listOpenIssues`** below;
the dependency-projection pair (`listIssueRelations` / `setIssueRelation`, fn-64.4) is
**§ Relation transport** below.

## ADF translation — Markdown ↔ Atlassian Document Format (the Jira body boundary)

Jira `/rest/api/3` issue **descriptions and comment bodies are ADF** (Atlassian
Document Format — `{"type":"doc","version":1,"content":[…]}`, confirmed to round-trip
exactly live 2026-06-28). The normalized structs ([adapter-interface.md](adapter-interface.md))
carry **free-form markdown**; reconcile (fn-52.4 body merge) only ever sees markdown.
So this adapter translates **markdown ↔ ADF at the boundary** — the Jira analog of
"reconcile stays transport-blind". `/rest/api/2` (DC/Server) bodies are **wiki/plain
text**, not ADF, so the translation is **gated on `$APIV == 3`** (§ DC/Server body
format below); on v2 the body passes through as wiki/plain text.

The translation is **lossy-but-faithful over a documented subset** with one
load-bearing rule: **never blind-regenerate ADF from markdown on a write** — that
drops every ADF node the subset doesn't model (panels, tables, media, custom marks a
human added in the Jira editor). Instead, **preserve unknown nodes verbatim** (§
Unknown-node preservation).

### The round-trip-safe subset (documented — what survives `markdown → ADF → markdown`)

| Markdown | ADF node/mark | Round-trips |
|---|---|---|
| paragraph | `paragraph` with `text` content | exact |
| `# … ######` heading | `heading` `attrs.level` 1–6 | exact |
| `**bold**` | `text` + mark `strong` | exact (verified live) |
| `*italic*` / `_italic_` | `text` + mark `em` | exact (normalizes to `*…*`) |
| `` `code` `` | `text` + mark `code` | exact (verified live) |
| `~~strike~~` | `text` + mark `strike` | exact |
| `[label](url)` | `text` + mark `link` `attrs.href` | exact |
| ` ```lang\n…\n``` ` fenced code | `codeBlock` `attrs.language` | exact |
| `> quote` | `blockquote` → `paragraph` | exact |
| `- ` / `* ` bullet list | `bulletList` → `listItem` → `paragraph` | exact |
| `1. ` ordered list | `orderedList` → `listItem` → `paragraph` | exact (numbering re-derived) |
| `---` thematic break | `rule` | exact |
| `<!-- … -->` HTML comment (the flow markers) | — (see note) | preserved as a verbatim text node, NOT an ADF node |

> **The flow markers survive because they are plain text, not ADF structure.** The
> `flow-evt:<event>` comment marker and the `<!-- flow-next:question id=… -->` /
> `<!-- flow-next:answer id=… -->` markers are HTML-comment **lines flow itself wrote**
> — they map to ordinary `text` nodes inside a `paragraph` and round-trip as literal
> characters (ADF has no concept of HTML comments, so they are carried as text). The
> marker scan in `listComments` runs on the **normalized markdown** the read direction
> produces, so a marker that round-tripped through ADF is still a plain `<!-- … -->`
> line when reconcile sees it. (Jira writes **no** `<!-- flow:deps -->` block — deps are
> native issue links — so there is no dep-block marker to preserve here.)

**Anything not in this table is "unknown"** — an ADF node type the subset doesn't
model (`panel`, `table`, `mediaSingle`/`media`, `expand`, `taskList`, `status`,
`emoji`, `mention`, `inlineCard`, a future node) or a mark the subset doesn't model.
Unknown nodes are **never** produced *from* markdown (markdown can't express them) but
DO appear on **reads** of a human-authored Jira body — and they MUST survive a
write-back.

### Read direction (ADF → markdown) — `fetchIssue` / `listComments`

`fields.description` (and each `comment.body`) on v3 is an ADF doc. Walk
`doc.content[]`; each known node renders to its markdown equivalent (table above);
each **unknown node renders to a placeholder token** carrying its **index** so the
write direction can splice the original ADF back in:

```
adfToMarkdown(doc):
  out = []
  for i, node in enumerate(doc.content):
    if node.type ∈ KNOWN_SUBSET:
       out.append( renderKnown(node) )           # markdown for the supported node
    else:
       out.append( "<!-- adf:unknown idx=" + i + " -->" )   # opaque placeholder, keeps position
  return join(out, "\n\n")
```

- The placeholder `<!-- adf:unknown idx=N -->` is itself an HTML comment, so it
  round-trips as text **and** the body-merge layer treats it as opaque (it is a flow
  marker, not human prose — reconcile never tries to "merge" it). The normalized
  markdown that reaches reconcile thus contains the human's editable prose **plus**
  position-keyed placeholders for the parts the subset can't represent.
- `status.raw`-style fidelity is preserved: a human reading the spec sees their
  editable content; the un-modelled panel/table is referenced by a placeholder rather
  than silently dropped or mangled.

### Write direction (markdown → ADF) — **fetch-current-first, splice, preserve unknowns**

On a body **write** (`writeIssue` UPDATE / a `postComment` that edits — though
comments are append-only, so this matters mainly for the description), the rule is
**fetch the current ADF FIRST, then splice** — never regenerate the whole doc from
markdown:

```
markdownToAdf(newMarkdown, currentAdf):                 # currentAdf from a fresh GET
  newBlocks = parseMarkdownBlocks(newMarkdown)          # blocks incl. the adf:unknown placeholders
  out = []
  for block in newBlocks:
    if block is an <!-- adf:unknown idx=N --> placeholder:
       out.append( currentAdf.content[N] )              # SPLICE the original ADF node back VERBATIM
    else:
       out.append( renderMarkdownBlockToAdf(block) )    # build ADF for the supported subset
  return { "type":"doc", "version":1, "content": out }
```

- **Unknown ADF nodes are carried through verbatim** — the placeholder the read
  direction emitted is replaced by the exact `currentAdf.content[N]` node, so the
  human's panel/table/media survives a flow write untouched. This is the
  no-silent-data-loss guarantee (R3): a flow push that only changed prose never
  destroys a Jira-editor-authored block.
- **Fetch the current ADF as part of the write path** — the UPDATE re-reads the issue
  to obtain `currentAdf` for the unknown-node splice. A **create** has no current ADF,
  so it builds the doc from the supported subset only (a fresh spec body has no
  human-authored unknown nodes yet).
- **A placeholder whose `idx` no longer resolves** (the current ADF changed shape
  between read and write, or the doc was edited concurrently so `content[N]` is a
  different node) is dropped to an empty paragraph rather than splicing the wrong node
  — never splice a mismatched index. (The body-merge base hash, fn-52.4, already
  guards the common concurrent-edit case; this is the defensive floor.)

### No `<!-- flow:deps -->` body block on Jira — deps are native issue links

Unlike the GitHub fenced fallback and the GitLab degraded tier, **Jira never writes a
`<!-- flow:deps -->` body block.** Dependency edges project as **native `Blocks` issue
links** (§ Relation transport), available on every Jira tier (Cloud + DC/Server, no
licensing gate — there is no Premium-only relation surface to degrade around). So the
description body carries no flow-owned dep region: the ADF write path preserves only
**unknown human-authored nodes** (above), never a dep block. (This is why the relation
collision check reads the native link listing, not a body block — § Relation transport.)

### DC/Server (`/rest/api/2`) body format — verify-at-build

On `/rest/api/2` (DC/Server, `$APIV == 2`) descriptions and comment bodies are **wiki
markup / plain text, NOT ADF**. So the ADF translation above is **gated on `$APIV ==
3`**; on v2 the body is carried as text (the `description`/`body` field is a plain
string, not an ADF doc). The exact v2 body representation (wiki-markup vs the
`renderer`/`representation` field on some DC builds) is **verify-at-build against the
Atlassian DC REST docs** (no DC instance was available to validate) — but the branch
is implemented now: `[ "$APIV" = 3 ] && body=ADF || body=text`. Unknown-node
preservation is an ADF-only concern (v2 has no node graph); on v2 the body is a
faithful text round-trip.

## Status / transitions — workflow-aware, via the transitions API (NEVER a direct set)

Jira has **rich, per-project configurable workflows** — you cannot `PUT fields.status`
to an arbitrary value. A status change goes through the **transitions API**: read the
transitions **legal from the issue's CURRENT status**, resolve the one that lands the
target, and POST its id. This is the GitLab/GitHub "reduced fidelity" inverted —
Jira's native model is *richer* than the normalized vocabulary, so the adapter maps
normalized → a project status via a configured `statusMap`, then drives the transition.

### `statusMap` — the FULL normalized set → Jira status `{id|name}`

`tracker.perTracker.statusMap` maps **each** normalized status to a Jira target. The
value is an **object** — `{"id": "10031"}` (preferred) or `{"name": "In Review"}` —
because Jira status **names are renamable** while the **id is durable** (same id-over-
name discipline as the durable `tracker.id`). It is the **full normalized set**, not
just ready/done:

> **Compare ids as STRINGS on BOTH the write match and the read reverse-map** (`| tostring`
> both sides). Jira returns status ids as strings, but an id refined via the dot-path
> (`flowctl config set tracker.perTracker.statusMap.done.id 10031`) is INT-coerced by
> `set_config`, so a bare `==` (string vs int) silently never matches. The whole-object
> JSON write (`config set …statusMap '{…}'`) keeps ids as strings; the `tostring` makes
> both forms work.

```jsonc
// tracker.perTracker.statusMap — normalized → Jira status (id preferred over name)
{
  "planned":     { "id": "10000" },          // e.g. "To Do"
  "in-progress": { "id": "3" },              // e.g. "In Progress"
  "in-review":   { "name": "In Review" },    // name when the id isn't pinned
  "done":        { "id": "10001" },          // a statusCategory.key=="done" status
  "verified":    { "id": "10002" }           // a second done-category status, if the project has one
  // backlog / deferred / wontfix — map only if the project has a lane for them
}
```

- **A normalized status with NO `statusMap` entry ⇒ defer + receipt, never force** —
  the adapter cannot invent a target. `sync defer --reason status-unmapped` (autonomous)
  / surface (interactive) + a `diverged` receipt; no transition is attempted.
- **A project lacking the target status entirely** (the canonical case: a team-managed
  project with **To Do / In Progress / Done and no "In Review"** — confirmed live
  2026-06-28) ⇒ **defer + receipt** (deterministic). The "nearest" status is **never
  inferred** — only an explicit configured fallback in `statusMap` may redirect it.
  This is the fn-66 sharp edge: the In-Review rung may simply not exist in a given
  project, and the adapter must defer it, not force the issue into an arbitrary lane.

### `setStatus(trackerId, status)` → ok | errored

```bash
# 1. Resolve the normalized status to a Jira target via statusMap (id preferred).
TARGET=$(printf '%s' "$STATUS_MAP" | jq -c --arg n "$NORMALIZED" '.[$n] // empty')
[ -z "$TARGET" ] && { sync_defer status-unmapped "$NORMALIZED"; return; }   # no entry → defer

# 1.5. ALREADY-CURRENT ⇒ NOOP (not defer). A push/status-only caller (work.firstClaim,
#      land.merged) may not have checked the current status; if the issue is ALREADY at
#      the target, Jira exposes no self-transition, so the step-3 lookup would otherwise
#      wrongly fall through to `transition-unreachable`. Read the current status and
#      string-match it the SAME way as step 3 (id tostring, else case-insensitive name):
CUR=$(curl -sS "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
        "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID?fields=status" | jq -c '.fields.status')
if printf '%s' "$CUR" | jq -e --argjson t "$TARGET" '
     ($t.id   != null and (.id   | tostring)      == ($t.id   | tostring)) or
     ($t.name != null and (.name | ascii_downcase) == ($t.name | ascii_downcase))' >/dev/null; then
  sync_receipt noop "status already at $NORMALIZED — no transition needed"; return
fi

# 2. Read the transitions LEGAL FROM THE CURRENT STATUS (ids are current-state-relative).
TRS=$(curl -sS "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
        "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID/transitions")
# → { transitions: [ { id, name, to: { id, name, statusCategory:{key} } }, … ] }

# 3. Find the transition whose .to matches the target (by id first, then name).
#    Compare ids as STRINGS (`| tostring` both sides): Jira returns `.to.id` as a string,
#    but a statusMap id refined via the dot-path (`config set …statusMap.done.id 10031`)
#    gets INT-coerced by set_config — so a bare `==` (string vs int) would never match.
TID=$(printf '%s' "$TRS" | jq -r --argjson t "$TARGET" '
        .transitions[] | select(
          ($t.id   != null and (.to.id | tostring) == ($t.id | tostring)) or
          ($t.name != null and (.to.name | ascii_downcase) == ($t.name | ascii_downcase))
        ) | .id' | head -1)

# 4. No legal transition reaches the target FROM HERE ⇒ defer + receipt, NEVER force.
[ -z "$TID" ] && { sync_defer transition-unreachable "$NORMALIZED"; return; }

# 5. Apply the transition (HTTP 204, no body).
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" \
  -X POST "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID/transitions" \
  --data @<(jq -n --arg id "$TID" '{ transition: { id: $id } }')
```

- **Transition ids are valid only FROM the current status** — you must `GET
  …/transitions` each time, never cache an id across statuses (verified live: To
  Do→In Progress→Done each surfaced different transition ids).
- **No legal transition to the target ⇒ defer + receipt, NEVER an illegal/forced
  jump** (`sync defer --reason transition-unreachable`; `diverged` receipt). This is
  the fn-66 "unreachable terminal transition" sharp edge: post-merge the In-Review→Done
  transition may be unreachable from the issue's current workflow state — the adapter
  surfaces it deferred, never forced, so a board is never stranded by a silent
  illegal-status attempt.
- **Prefer the durable status `id`** in `statusMap` and in the `.to.id` match; the
  name match is the fallback for an unpinned config (`statusMap.<n>.name`).

### Terminal detection = `statusCategory.key == "done"` (NOT the status name)

```bash
# fetchIssue already pulled fields.status — terminal is the CATEGORY, not the name.
TERMINAL=$(printf '%s' "$ISSUE_JSON" | jq -r '.fields.status.statusCategory.key == "done"')
```

- **`statusCategory.key ∈ { new, indeterminate, done }`** is the stable signal: status
  *names* are project-specific and renamable ("Done" may be renamed "Shipped"), while
  the category key is fixed. A `done`-category status is terminal; `new`/`indeterminate`
  are non-terminal. (Confirmed live 2026-06-28 — the spec's name-based detection was
  wrong; category is the durable signal.)

### `readStatus` — reverse-map (the inverse of the write `statusMap`)

`readStatus` normalizes the Jira status BACK to the flow vocabulary — the inverse of
the write map. Resolution order:

1. **Reverse `statusMap`** — find the normalized key whose `statusMap` value matches
   `fields.status`: **`id` first, compared as STRINGS** — `(fields.status.id | tostring)
   == (entry.id | tostring)` — because a `statusMap` id refined via the dot-path
   (`config set …statusMap.done.id 10031`) is int-coerced by `set_config`, so a bare
   `==` against Jira's string id would never match (identical rule to the `setStatus`
   write match, § above); **then case-insensitive `name`**. This is the authoritative
   reverse (a project's "In Review" → `in-review`).
2. **`statusCategory.key` fallback** when no `statusMap` entry matches (a status the
   map doesn't cover): `done` → `done`; `new`/`indeterminate` → a **safe non-terminal**
   (`planned` / `in-progress` respectively) **only when unambiguous** — never guess a
   `verified`/`in-review` rung from a category alone.
3. **Unmapped** (neither the map nor an unambiguous category fallback resolves it) ⇒
   **defer + receipt** (`sync defer --reason status-unmapped`), `status.normalized`
   left unresolved — the same warn-and-surface posture as the Linear unmapped-state
   path ([status-sync.md](status-sync.md)). The other fields still reconcile.

`status.raw = fields.status.name` (the literal Jira name, for the sync log);
`status.normalized` = the reverse-map result (or unresolved → deferred).

### fn-66 terminal invariant — transport-blind, honored DOWN through statusMap

The terminal-status invariant ([adapter-interface.md](adapter-interface.md) §
Transport-blind terminal invariant; [status-sync.md](status-sync.md)) is **upstream
and transport-blind**: `flowToNormalized(spec, prEvidence)` only ever hands this
adapter a terminal `done`/`verified` AFTER a `MERGED` PR probe for the spec branch.
This adapter therefore:

- **never decides terminal from local spec state** — a locally-`done` spec with no
  merged PR arrives as **`in-review`** (the open-PR rung), which `statusMap` maps to
  the project's In-Review status and the transitions API applies. The issue is NOT
  closed.
- maps a gated terminal `done`/`verified` DOWN through `statusMap` to a
  `statusCategory.key == "done"` status and drives the transition — only after the
  merge gate, never re-deciding it here.
- surfaces a **deferred** terminal transition (the In-Review→Done transition
  unreachable from the current workflow state) via receipt, **never** a forced jump —
  the unreachable-transition defer rule above IS the fn-66 "deferred terminal
  transition" surface.

## Relation transport (dependency projection, fn-64)

`depends_on_epics` edges project to **blocked-by** relations via Jira native **issue
links** — `POST /rest/api/$APIV/issueLink` with the `Blocks` link type. Jira native
links are first-class and directional (unlike GitLab's license-gated tiers), so there
is **one** fidelity here — no degrade ladder. The direction convention is anchored
once in [adapter-interface.md](adapter-interface.md) § Direction convention:

> **blocked-by = the current issue (A) is blocked by the dependency issue (B).**

### Native facts (pin these — verified live 2026-06-28)

- **`POST /rest/api/3/issueLink`** with `{type:{name:"Blocks"}, outwardIssue:{key|id},
  inwardIssue:{key|id}}` returns **HTTP 201**. `outwardIssue` **blocks** `inwardIssue`
  → `inwardIssue` shows **"is blocked by"**. So for `depends_on`: the **dependency B**
  is `outwardIssue` (it blocks), the **current issue A** is `inwardIssue` (it is
  blocked). Pass the durable `id` for both operands (key also accepted).
- **`GET /rest/api/$APIV/issue/{idOrKey}?fields=issuelinks`** returns
  `fields.issuelinks[]`, each `{ type:{name,inward,outward}, inwardIssue?, outwardIssue? }`
  — an entry has `outwardIssue` XOR `inwardIssue` depending on the direction from the
  inspected issue's perspective.
- **Jira does NOT no-op a duplicate `POST /issueLink`** — re-posting the same edge
  creates a second link. **Read-before-write dedup is mandatory** (below).
- **DELETE (`DELETE /rest/api/$APIV/issueLink/{linkId}`) is OPTIONAL / future** — not
  implemented (default-safe no-delete; never removes a remote relation — R6).

### `listIssueRelations(issue)` → normalized `relation[]`

```bash
curl -sS "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
  "$JIRA_BASE/rest/api/$APIV/issue/$A_ID?fields=issuelinks" \
  | jq -c --arg A "$A_ID" '.fields.issuelinks[]
           | select(.type.name == "Blocks")        # ONLY the blocked-by edge kind
           | if .inwardIssue then
               # A "is blocked by" B → A is blocked (from), B is the blocker (to)
               { from: $A, to: .inwardIssue.id, type: "blocks", source: "unknown", linkPresent: true }
             elif .outwardIssue then
               # A "blocks" B → the inverse edge; B is blocked (from), A is the blocker (to)
               { from: .outwardIssue.id, to: $A, type: "blocks", source: "unknown", linkPresent: true }
             else empty end'
```

The jq **emits the normalized `relation` directly** — `type: "blocks"` (so
`setIssueRelation`'s read-before-write dedup matches on `.type == "blocks"`),
`source: "unknown"` (Jira native links store no flow authorship → the ledger is the
provenance authority), `linkPresent: true` (a Jira native link IS the visible
projection; it never orphans). Shape ([adapter-interface.md](adapter-interface.md) §
`relation`):

```jsonc
{ "from": "<blocked A id>", "to": "<blocker B id>", "type": "blocks",
  "source": "unknown",        // Jira native links store NO flow authorship → ledger is authority
  "linkPresent": true }        // a Jira native link IS the visible projection; it never orphans
```

- **`linkPresent` is ALWAYS `true`** (mandatory field, fn-69). A Jira native link is
  the tracker-visible projection itself — there is **no** GitLab-style block/link
  divergence here (Jira writes one native link, not a link **plus** a separate body
  block), so a relation never reads as orphaned `linkPresent: false`. Setting it
  unconditionally is required: a producer that omitted it would make every Jira live
  relation read as falsy → misclassified as orphaned.
- **`source` is `"unknown"`** — Jira native links carry no authorship, so (like
  Linear/GitHub-native/GitLab-native) the flow-side `depRelations` **ledger** (fn-64.1)
  is the provenance authority for "did flow create this?". Provenance is never inferred
  from `source` alone.
- **Only `type.name == "Blocks"` edges are returned.** Other Jira link types
  (`Relates`, `Duplicate`, `Cloners`, …) are NOT relations in the flow sense and are
  filtered out, so the read-before-write dedup never trips over an unrelated edge.

### `setIssueRelation(issue=A, blockedBy=B)` → ok | errored | noop

**Read-before-write dedup (mandatory, R3)** — Jira does not no-op a duplicate, so
`listIssueRelations(A)` FIRST and skip the write when the (A blocked-by B) edge is
already present as a native link:

```bash
EXISTS=$(listIssueRelations "$A_ID" | jq -s --arg b "$B_ID" \
           'any(.[]; .from == "'"$A_ID"'" and .to == $b and .type == "blocks")')
[ "$EXISTS" = true ] && { sync_receipt noop "relation already linked (A blocked-by B)"; return; }
```

**Defer-on-human-removal collision (R6/R10).** The dedup reads the **tracker-visible
native link**, not the ledger. When the flow `depRelations` ledger records the (A,B)
edge but the **native link is gone** (a human deleted the board-visible "is blocked by"
link), that is a **human-removal collision**, NOT a missing projection to re-create:
**queue it, default NOT re-create** (autonomous → `sync defer --reason dep-link-removed`;
interactive → surface/ask whether to restore or honor the removal). **Never silently
re-create** — recreating steamrolls a deliberate human removal (the explicit
anti-behavior; the shared steps.md `projectDepRelations` rule, hardened in fn-69).
Restore ONLY on the human's explicit choice.

```bash
# Ledger says we projected (A,B) but the native link is absent → human removed it → defer.
LEDGERED=$($FLOWCTL sync list-dep-relations "$SPEC_ID" --json | jq --arg b "$B_TRACKER_ID" \
             'any(.relations[]?; .to_tracker_id == $b)')
if [ "$LEDGERED" = true ] && [ "$EXISTS" != true ]; then
  $FLOWCTL sync defer "$SPEC_ID" --reason dep-link-removed \
    --summary "Blocked-by link A→B removed on the tracker (ledgered but no native link)" \
    --suggested "Restore the link, or accept the human removal and drop the dep edge"
  $FLOWCTL sync receipt "$SPEC_ID" --status diverged --transport "$TRANSPORT" ${EVENT:+--event "$EVENT"} \
    --note "dep link A blocked-by B removed on tracker — queued, NOT re-created"
  return
fi

# Otherwise CREATE the link (additive-only). DIRECTION — LIVE-VALIDATED 2026-06-28
# (FINDINGS-jira.md): `outwardIssue` **blocks** `inwardIssue`; `inwardIssue` shows
# "is blocked by". The edge is "A is blocked by B" (A=current/blocked, B=dep/blocker),
# so the BLOCKER B = outwardIssue (it blocks) and the BLOCKED A = inwardIssue (it is
# blocked by). Hence out=$B_ID, in=$A_ID — do NOT swap (a fetched link on A then reads
# back `inwardIssue: B` ⇒ "A is blocked by B", exactly what listIssueRelations expects).
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -X POST "$JIRA_BASE/rest/api/$APIV/issueLink" \
  --data @<(jq -n --arg out "$B_ID" --arg in "$A_ID" \
              '{ type: {name:"Blocks"}, outwardIssue:{id:$out}, inwardIssue:{id:$in} }')
# → HTTP 201. Record the projected edge in the ledger (flowctl sync set-dep-relation).
```

- **Additive-only / never-delete-non-ours (R6).** `setIssueRelation` only ever
  **creates** the blocked-by link. A native link not in the `depRelations` ledger is,
  by definition, not flow's and is never touched.
- **Completed-blocker (R5).** A dependency whose spec is locally `done` stays a
  visible blocked-by link (a closed blocker still renders); it is NOT removed and does
  NOT feed `ready=true` gating. The decision is the skill's (fn-64.5), keyed off the
  **local** `dep_status` (`flowctl sync list-dep-relations`), not a remote fetch.
- **No-transport** ⇒ `noop` + receipt note (the terminal rung), never a crash.

## `listOpenIssues(filter)` → `issue[]` (fn-68 — enumeration), endpoint by `apiVersion`

Enumerate the **promoted lane** — open issues at the exact `tracker.readyState` **Jira
status name** — via JQL. The `readyState` is the **tracker-side promoted-lane value
used RAW in the JQL** (a literal Jira status name, like Linear/GitHub readyState),
**NOT** resolved through `statusMap` ([adapter-interface.md](adapter-interface.md) §
Enumeration transport — the exact lane, no ordering).

**`tracker.readyState` unset ⇒ documented `noop` (return `[]`)** — no promoted lane to
filter on (the skill, steps.md Phase 7a, short-circuits before calling the transport).
`TRANSPORT=none` ⇒ `noop` + receipt note, `[]`.

### JQL safety (mandatory — no injection)

`readyState` and `projectKey` are interpolated into JQL, so both MUST be sanitized:

```bash
# 1. projectKey — validate against the Jira key grammar (uppercase alnum, starts with a
#    letter: ^[A-Z][A-Z0-9]+$). Reject anything else (no JQL injection via the key).
printf '%s' "$PROJ_KEY" | grep -Eq '^[A-Z][A-Z0-9]+$' \
  || { sync_receipt errored "invalid projectKey '$PROJ_KEY' — not a Jira key"; return; }

# 2. readyState — escape backslashes THEN double-quotes for the JQL string literal
#    (order matters: backslash first, else the quote-escape's backslash gets doubled).
READY_ESC=$(printf '%s' "$READY_STATE" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
JQL="project = $PROJ_KEY AND status = \"$READY_ESC\""
```

### Cloud v3 — `POST /rest/api/3/search/jql` + cursor pagination

The legacy `GET /rest/api/3/search` returns **HTTP 410 REMOVED** (CHANGE-2046,
confirmed live 2026-06-28). The real call is **`POST /rest/api/3/search/jql`** with a
JSON body, paginated by an opaque **cursor** (`nextPageToken`), NOT the legacy
`startAt`/`total` offset:

```bash
NEXT=""; PAGE=0; MAXP=20    # bounded page count; a truncating bound writes a receipt note
while :; do
  BODY=$(jq -n --arg jql "$JQL" --arg tok "$NEXT" \
           '{ jql: $jql, maxResults: 100,
              fields: ["summary","description","status","priority","labels","updated"] }
            + ( if $tok == "" then {} else { nextPageToken: $tok } end )')
  RESP=$(curl -sS "${JK[@]}" "${JAUTH[@]}" \
           -H "Content-Type: application/json" -H "Accept: application/json" \
           -X POST "$JIRA_BASE/rest/api/3/search/jql" --data @<(printf '%s' "$BODY"))
  printf '%s' "$RESP" | jq -c '.issues[]'    # map each → normalized issue (firewall)
  ISLAST=$(printf '%s' "$RESP" | jq -r '.isLast // true')
  NEXT=$(printf '%s' "$RESP" | jq -r '.nextPageToken // empty')
  PAGE=$((PAGE+1))
  { [ "$ISLAST" = true ] || [ -z "$NEXT" ] || [ "$PAGE" -ge "$MAXP" ]; } && break
done
# PAGE >= MAXP with more pages → truncation receipt note (never silently under-read).
```

- **Pass the returned `nextPageToken` in the next request body until `isLast: true`**
  (or the token is empty). Bounded by `MAXP`; a truncating bound writes a **receipt
  note**, never a silent under-read of the promoted lane.

### DC/Server v2 — `/rest/api/2/search` (implemented now, verify-at-build)

DC/Server (`$APIV == 2`) uses the **`/rest/api/2/search`** endpoint. The Cloud 410
removal is a **Cloud-only** change (CHANGE-2046 targets Cloud); DC/Server retains the
classic search with **offset pagination** (`startAt` / `maxResults` / `total`). This
is **implemented now** (R1/R9 require all nine methods for DC — NOT deferred); the
exact endpoint + body shape is **verify-at-build against the Atlassian DC REST docs**
(no DC instance was available to validate):

```bash
START=0; MAXR=100; MAXTOTAL=2000   # bounded; a truncating bound writes a receipt note
while :; do
  # DC classic search — likely GET with query params, or POST /search with a JSON body.
  RESP=$(curl -sS "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
           --data-urlencode "jql=$JQL" --data-urlencode "startAt=$START" \
           --data-urlencode "maxResults=$MAXR" \
           --data-urlencode "fields=summary,description,status,priority,labels,updated" \
           -G "$JIRA_BASE/rest/api/2/search")
  printf '%s' "$RESP" | jq -c '.issues[]'    # map each → normalized issue
  TOTAL=$(printf '%s' "$RESP" | jq -r '.total // 0')
  START=$((START + MAXR))
  { [ "$START" -ge "$TOTAL" ] || [ "$START" -ge "$MAXTOTAL" ]; } && break
done
# START >= MAXTOTAL with more results → truncation receipt note.
```

- **Branch on the persisted `$APIV`**: `3` → the Cloud cursor path; `2` → this DC
  offset path. The deltas (exact verb, body shape, `nextPage` field name on newer DC
  builds) are flagged **verify-at-build** — but the offset-pagination path IS
  implemented, not deferred.
- **Map each `.issues[]` into the normalized `issue` struct** via the same firewall
  table `fetchIssue` uses (ADF descriptions translated on v3 — § ADF translation).
  **Linkage is decided authoritatively by the local sync state** (the recorded linked
  tracker-ids), NOT by the `flow:<id>` label's presence — the label is a corroborating
  hint only; a bounded/truncated label set is never read as "unlinked".

## `makePr` — link the PR to the issue as a **remote link** (in-adapter)

When the tracker is **Jira**, the spec maps to a Jira *issue* and the PR lives in a
git host (GitHub/GitLab) Jira does not natively cross-reference. Jira has **neither**
GitHub's `Refs #N` auto-linkify **nor** Linear's auto-detected Diffs attachment, and
**Smart-Commit `PROJ-123` keys are not relied on** (they need a DVCS connector that
may be absent). So the make-pr PR link projects to Jira as a **remote link** written
**in-adapter** — the In-Review-rung evidence equivalent:

```bash
# POST a remote link carrying the PR url + a title. HTTP 201 (confirmed live 2026-06-28).
# IDEMPOTENT via globalId: Jira UPSERTS a remote link keyed on globalId (POST updates the
# existing one rather than creating a duplicate), so repeated makePr / retro-fire /
# reconcile runs REFRESH the same link instead of stacking duplicates. Derive globalId
# deterministically from flow-next + the PR url (stable across runs for this PR).
curl -sS -w '\n%{http_code}' "${JK[@]}" "${JAUTH[@]}" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -X POST "$JIRA_BASE/rest/api/$APIV/issue/$TRACKER_ID/remotelink" \
  --data @<(jq -n --arg url "$PR_URL" --arg title "$PR_TITLE" --arg gid "flow-next:pr:$PR_URL" \
              '{ globalId: $gid, object: { url: $url, title: $title } }')
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
  the same In-Review status push the other adapters do (the status push itself is the
  transitions model in § Status / transitions above); the remote link is the link half
  and is owned here.
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
- **fn-70.2 authored the transport + six core + auth + identity + PR remote-link;
  fn-70.3 added the ADF translation, the transitions/status model (incl. the fn-66
  terminal gate), the relation pair, and `listOpenIssues`** — the full nine-method
  interface is now implemented here.
- **The readiness projection's Jira branch is in [status-sync.md](status-sync.md)**
  (the one additive carve-out to "status-sync untouched") — a name-match like Linear
  (`DESIRED = status name == readyState`) + the stale-config existence check, mirroring
  fn-69's GitLab branch. It is distinct from the `listOpenIssues` JQL filter (the
  promoted-lane enumeration) and from the ceremony's readyState collection.
- **No new hard dependency.** Only `curl` + `jq` (already required by the bridge); the
  terminal rung is a documented no-op. The zero-dep base install is untouched
  (STRATEGY opt-in carve-out).
- **One Jira issue per linked spec** (`tracker.perTracker.baseUrl` + `projectKey`) —
  the bridge config resolves a single site/project, mirroring the one-team Linear /
  one-repo GitHub constraint.
- **Codex mirror** (sync-codex.sh) is regenerated in fn-70.4 — keep this file
  Claude-native; no Codex-specific edits here.
