# GitLab adapter — transport via `glab` (headless-safe, reduced-fidelity status)

The GitLab implementation of the nine-method transport interface
([adapter-interface.md](adapter-interface.md)) — the original six core methods, the
dependency-projection pair (`listIssueRelations` / `setIssueRelation`, fn-64), plus
the enumeration method (`listOpenIssues`, fn-68). Modelled section-for-section on
the **GitHub adapter** ([github.md](github.md)): GitLab, like GitHub, is a git host
with a thin open/closed issue workflow, so the `gh`/single-rung + reduced-status
template fits far better than Linear's MCP-first rich-workflow ladder
([linear-ladder.md](linear-ladder.md)). It reuses the reconcile core
(fn-52.4 body merge, fn-52.5 status/comments) **unchanged** — proving the
reconciliation is transport-blind (the R13 guarantee). Unlike GitHub's single `gh`
rung, GitLab has a **two-rung** ladder — `glab` first, a raw-REST token fallback
second — plus the terminal no-op. **Endpoints/limits verified live 2026-06-28**
(`~/work/agent-scripts/flow-smoke/out/FINDINGS-gitlab.md`).

| Rung | Transport | Use when | Notes |
|------|-----------|----------|-------|
| 1 | **`glab api <path>`** (headless via `GITLAB_TOKEN`/`CI_JOB_TOKEN`, or a stored `glab auth login`) | `glab auth status` exits 0 (a credential resolves) | the **primary** GitLab transport — glab's stored auth + the full `/api/v4` REST surface, **including issue links** the `glab issue` subcommand **lacks**. Scriptable JSON via `-O json --jq` (NOT `-F`). |
| 2 | **raw REST `/api/v4`** (headless via `GITLAB_TOKEN`/`CI_JOB_TOKEN`) | `glab` absent but an env token is set | the same `/api/v4` surface without glab — header ladder below; the CI/headless floor when glab is not installed |
| 3 (terminal) | **no-op + receipt note** | no `glab` credential AND no env token | the bridge is configured but no GitLab transport is reachable |

The chosen rung is recorded on every receipt: `sync receipt … --transport glab|rest|none`
— plus, on a lifecycle run, the touchpoint it served: `${EVENT:+--event "$EVENT"}`
(`$EVENT` is set in steps.md Phase 0; empty on manual runs, so the flag is omitted).
The agentic reconciliation (fn-52.4 body merge, fn-52.5 status/comments) is
**identical regardless of tracker** — that is the R13 guarantee, and the parity
check below (vs the GitHub adapter) is how it is verified.

> **Why `glab` and not the REST API directly.** `glab` is the headless,
> auth-managed analog of `gh`: it reads `GITLAB_TOKEN`/`GITLAB_HOST` from the
> environment (or a stored `glab auth login`), drives the **full** `/api/v4`
> surface through `glab api <path>`, and reuses the session a developer (or a CI
> job) already has — **zero flow-next-specific provisioning** (verified: with
> `GITLAB_TOKEN` set, `glab api` / `glab issue` work with **no** `glab auth
> login`). The raw-REST rung is the same surface for hosts where `glab` is not
> installed; both speak `/api/v4`, so the adapter logic is identical and only the
> *invocation* differs.

> **No MCP rung — available but deliberately unused (decided 2026-06-28).** GitLab
> ships an *official* built-in MCP server (GitLab 18.7+) covering GitLab.com,
> Self-Managed, and Dedicated — but it requires **Premium/Ultimate + OAuth 2.0**,
> so it is not universal. `glab` + a PAT / `CI_JOB_TOKEN` covers self-managed at
> **every** license tier with zero setup, so this adapter stays CLI-only
> (GitHub-shaped) and adds **no** agentic MCP rung. This note records the MCP route
> as *available-but-not-wired* so a future spec can revisit without re-researching;
> nothing here depends on it.

## Rung detection (probe, don't assume)

Detection lives in the skill (host agent), not in flowctl — same shape as fn-51's
driver ladder and the GitHub/Linear ladders. The tracker + credential are confirmed
**once at the discovery ceremony** and persisted to config (`env > config`,
mirroring `cmd_review_backend`); the runtime `glab → token` order is a cheap
reachability check (no MCP, no support-probe), never a per-run re-selection. Probe;
take the first rung that passes:

```bash
# Rung 1 — glab reachable + authenticated. `glab auth status` exits 0 when a
# credential resolves for the host — from EITHER a stored `glab auth login`
# (the gh-style zero-setup path: a logged-in dev needs NO flow-env token) OR
# GITLAB_TOKEN / CI_JOB_TOKEN in the environment (glab reads env too — no
# `glab auth login` required). `glab api` drives IDENTICALLY regardless of the
# credential source. The discovery probe in SKILL.md uses this same signal.
if command -v glab >/dev/null 2>&1 && glab auth status >/dev/null 2>&1; then
 TRANSPORT=glab
# Rung 2 — glab absent but an env token is set → raw REST against /api/v4.
elif [ -n "$GITLAB_TOKEN" ] || [ -n "$CI_JOB_TOKEN" ]; then
 TRANSPORT=rest
fi

# Rung 3 — neither reachable:
# TRANSPORT=none → every interface method is a documented no-op + receipt note.
TRANSPORT="${TRANSPORT:-none}"
```

Headless usage: set `GITLAB_TOKEN` (a PAT or fine-grained token) — or `CI_JOB_TOKEN`
in CI — in the environment; `glab` is then fully non-interactive (no browser, no
prompt) and the raw-REST rung needs no glab at all. This is the Ralph/cron/CI path.
(Verified 2026-06-28: with neither a stored login nor a token, `glab auth status`
reports "no token found" → 401 → the adapter's no-op rung.)

### Host resolution (self-managed — never assume gitlab.com)

GitLab is heavily self-managed; **never hardcode gitlab.com**. Resolve the host
once and derive the REST base from it:

- **Host:** `tracker.perTracker.host` (config) → `GITLAB_HOST` → `glab config get
 host` → `CI_SERVER_URL` (CI). On the `glab` rung, glab's own configured host is
 authoritative; on the REST rung, the resolved host drives the base URL.
- **REST base = `<host>/api/v4`**, never a hardcoded `gitlab.com` base. The
 `glab api <path>` rung speaks **relative** REST paths (e.g. `projects/:id/issues`)
 and glab prepends its host, so the same path string works on both rungs.

### Self-managed TLS (opt-in escape hatch, never silent)

On-prem GitLab often presents an internal-CA / self-signed cert. `glab` uses its
own host trust, so the `glab` rung usually just works. For the **raw-REST** rung,
honor an explicit, opt-in TLS-skip escape hatch (glab's `skip_tls_verify` config or
a documented `GITLAB_SKIP_TLS_VERIFY` env flag → the REST call adds `curl -k` / the
equivalent) — **never silent**, so an internal-CA host is not a hard failure but the
user must consciously opt in. Default is full TLS verification.

### Token scope (verified 2026-06-28) — least-privilege, never depend on `GET /user`

- **Classic PAT** needs the **`api`** scope (full read/write).
- **Fine-grained token** needs only **project** permissions (issue read/write).
 Verified: a project-scoped fine-grained token with **0 user permissions** does
 `GET`/`POST /projects/:id/issues` fine (`GET /user` 403s with
 `insufficient_granular_scope`, "requires [User: Read]"). So the adapter **MUST
 NOT** depend on `GET /user` or any user-level scope — a project-scoped token
 (issue r/w) is sufficient and least-privilege.
- A genuinely missing **project** permission fails with a clear **`403
 insufficient_granular_scope`** — surface it **verbatim** so the user knows exactly
 what to grant.
- **`CI_JOB_TOKEN`** is allowlist-limited per the CI job-token allowlist and may be
 **read-only** for issues/labels in arbitrary projects. Writes that 403 ⇒ degrade
 to the **no-op rung + receipt note** (degrade writes, never over-promise — R2).

### Header ladder (raw-REST rung only)

`glab api` handles auth itself; the header ladder is **only** the raw-REST fallback.
The token *kind* selects the header — getting this wrong is a silent 401:

| Credential | Header | Notes |
|---|---|---|
| `GITLAB_TOKEN` (classic PAT or fine-grained) | **`PRIVATE-TOKEN: <tok>`** | the standard PAT header |
| `CI_JOB_TOKEN` | **`JOB-TOKEN: <tok>`** | **NOT** `PRIVATE-TOKEN` — CI job tokens authenticate via `JOB-TOKEN` |

### Project-path encoding (BOTH rungs — verified, a literal slash 404s)

The `project` config (`tracker.perTracker.project`) is a group/project path
(`group/project`, or nested `group/subgroup/project`). It **MUST be URL-encoded**
(`group%2Fproject`, `group%2Fsubgroup%2Fproject`) wherever it appears in a REST
path — for **both** `glab api` **and** raw REST. Verified 2026-06-28: `glab api
projects/group/project` **404s**; only `projects/group%2Fproject` (or the numeric
project id) works.

- **Store the `project` literal; derive `encodedProject` once** (replace every `/`
 with `%2F`); **never double-encode** (encoding an already-encoded `%2F` yields
 `%252F`, which also 404s). The numeric project id (resolved once via `GET
 /projects/<encodedProject>`) is an alternative that needs no per-call encoding.

## No-op rung (terminal) — never crash

When `TRANSPORT=none`, the configured bridge cannot reach GitLab this run. Every one
of the nine interface methods becomes a documented no-op (same fail-soft contract as
the GitHub/Linear terminal rungs and fn-51's manual rung) — including
`listOpenIssues` (returns `[]`, fn-68) and the relation pair (fn-64):

- `fetchIssue` / `listComments` / `readStatus` / `listIssueRelations` /
 `listOpenIssues` → return nothing actionable ("no remote view available this
 run"); the spec's flow-side state is left untouched and the merge base is NOT
 advanced.
- `writeIssue` / `postComment` / `setStatus` / `setIssueRelation` → perform no
 remote write.
- The run emits `sync receipt … --status noop --transport none ${EVENT:+--event "$EVENT"}
 --note "no GitLab transport reachable (glab not installed/authed and no GITLAB_TOKEN/CI_JOB_TOKEN)"`.
- `lastSyncedAt` is never advanced on a no-op (no real reconciliation happened).

A **`CI_JOB_TOKEN` write that 403s** for scope reasons degrades that *write*
operation to the same no-op + receipt note (read ops may still have succeeded on the
token's allowlisted scope) — the run never fails hard.

## `glab` / REST connection facts (pin these — they have sharp edges)

- **Auth (headless):** `GITLAB_TOKEN` (PAT or fine-grained, preferred for
 non-interactive) or `CI_JOB_TOKEN` in CI; `glab` reads both from the environment
 with **no `glab auth login`** (verified). `glab auth status` exits 0 iff a
 credential resolves; the exit code is the load-bearing probe signal. Never prompt
 — a missing credential ⇒ the no-op rung, not an interactive login.
- **Primary mechanism is `glab api <REST path>`** — the `gh api` equivalent: glab's
 stored auth + the full `/api/v4` surface, **including issue links** that the `glab
 issue` subcommand **lacks** (verified — `glab issue` has no link/relate/block
 command). `glab issue`/`glab mr` cover convenience ops (create/list/view/note).
- **JSON flag is `-O json` / `--output json`** (+ `--jq` for projection), **NOT
 `-F json`** (`-F`/`--output-format` is details/ids/urls, a different flag).
- **Project target:** every REST path needs the **URL-encoded** project
 (`encodedProject`) — see the encoding rule above. The bridge config's
 `tracker.perTracker.project` supplies the literal path.
- **Bodies via `--body-file -` (or piped stdin), NEVER raw inline.** GitLab issue
 bodies are **GitLab-Flavored Markdown** (the same family as GitHub) — backticks,
 `$`, newlines, and quotes break shell quoting on an inline body argument. Write
 the body to a temp file (or pipe stdin) and pass `--body-file -`. **No ADF
 translation layer is needed** (GFM is a plain markdown string — verified —
 unlike Jira's ADF). This is the GitLab analog of github.md's `--body-file -`
 discipline; same failure mode (escaping mangles the round-trip), same fix.
- **id vs iid:**
 - **Durable dedupe key = the global issue `id`** (immutable, project-independent —
 NOT the project-local `iid`) from `--jq .id`. Store it via `sync set-tracker-id`.
 - `<project>#<iid>` (`iid` = the project-local display number) is the display key
 (the normalized `identifier`); surface it to humans. The `iid` is **only unique
 within a project**, which is exactly why the global `id` is the durable key —
 moving/relating across projects keeps the global `id` stable.
 - The REST issue path takes the **`iid`** (`/projects/:id/issues/:iid`); the
 global `id` is for storage/dedup, not for the path.
- **State is two-valued + `closed_at`** (the fidelity gap — see below): `state` →
 `opened` | `closed`; a `PUT {state_event: close|reopen}` flips it (verified —
 `closed_at` is set on close, cleared on reopen).
- **Comments carry a `system` flag** (verified): `GET /issues/:iid/notes` items have
 `system: true|false`. `system==true` are GitLab **automated events** (label
 changes, state changes, …) — **filter them out** on pull; only `system==false` are
 human comments (see `listComments`).
- **Rate limit / transient errors** — GitLab returns **HTTP 429** (or transient
 5xx) with a `Retry-After` / `RateLimit-Reset` header. `glab`/`curl` surface a
 non-zero exit. **Bounded retry** (exponential, honor the reset hint), then **defer
 + receipt** rather than failing the run — same non-destructive contract as the
 other adapters (R11/R12).

## State fidelity — reduced (the key GitLab difference, same as GitHub)

GitLab native state is only **`opened`/`closed`** (+ `closed_at`), with optional
**board labels** — not a rich, team-defined workflow taxonomy like Linear. The
flow normalized vocabulary (`backlog` · `planned` · `in-progress` · `in-review` ·
`done` · `verified` · `deferred` · `wontfix`) is **richer than GitLab can natively
represent**. So the GitLab adapter, exactly like GitHub:

1. **Maps the normalized status DOWN to GitLab's two-value native state** (what
 `setStatus` writes via `PUT {state_event}`), and
2. **Carries the fine-grained status as a label** (`status:in-progress`,
 `status:in-review`, …) so the full flow status survives a round-trip and
 `readStatus` can recover it.

### Read (`readStatus` / `fetchIssue` → normalized `status`)

Prefer the `status:` label when present (it carries full fidelity); fall back to
native `state` when no `status:` label exists (e.g. an issue closed directly on
GitLab by a human who didn't touch the label):

| GitLab native (`state` + `closed_at`) | `status:` label present? | normalized | who-wins ([status-sync.md](status-sync.md)) |
|---|---|---|---|
| `opened` | `status:<x>` | use the label's `<x>` (`in-progress` / `in-review` / `planned` / `backlog`) | per fn-52.5 |
| `opened` | none | `in-progress` (best-effort default for an open issue) | flow wins |
| `closed` | `status:done` / `status:verified` | use the label's `<x>` (so `verified` vs `done` is recoverable) | tracker wins |
| `closed` | none | `done` (GitLab has no close-reason; a reasonless close is treated as completed) | tracker wins |

> **GitLab has no `stateReason`/`NOT_PLANNED` analog** (unlike GitHub). A `closed`
> issue with no `status:` label normalizes to **`done`**; the `wontfix` / `deferred`
> distinction lives **only** in the `status:` label (set by flow on a surfaced,
> human-confirmed transition — never auto-applied, see Write below), since GitLab
> offers no native "not planned" close to read it back from.

`status.raw` = the literal GitLab signal (e.g. `"closed"` or the `status:` label
text) for the sync log; `status.normalized` = the table result.

### Write (`setStatus` — map normalized DOWN)

| normalized | GitLab native action | `status:` label |
|---|---|---|
| `backlog` / `planned` / `in-progress` / `in-review` | ensure **opened** (`PUT {state_event:reopen}` if closed) | set `status:<normalized>` (remove any other `status:*`) |
| `done` / `verified` | `PUT {state_event:close}` | set `status:<normalized>` (so `verified` vs `done` is recoverable) |
| `deferred` / `wontfix` | **do NOT auto-apply** — these are R7 surface-only | — |

**Terminal close requires merge evidence (R1, R8 — same gate as GitHub/Linear).**
The `done`/`verified` row is a *transport* mapping: the adapter only ever *receives*
a terminal normalized status because the upstream `flowToNormalized(spec,
prEvidence)` map ([status-sync.md](status-sync.md)) gated it on a `MERGED`
merge-evidence probe for the spec branch. A locally-`done` spec with no merged
PR/MR normalizes to **`in-review`** (→ opened issue + `status:in-review`), so this
adapter **never closes the issue** for a spec lacking merge evidence. The
merge-evidence gate is transport-blind (R8); this firewall just maps the
already-gated status DOWN to GitLab's `opened`/`closed`. No `PUT {state_event:close}`
is ever driven from local completion alone.

**`deferred` / `wontfix` are surfaced, never auto-applied** (R7 semantics, same as
GitHub's `not planned`): the adapter reports the desired transition to the user (or
queues it in Ralph) rather than closing the issue unilaterally. A human confirms a
`wontfix`/`deferred` close. The read-mapping above interprets a label a human set; the
write side only auto-writes the open / completed-close transitions.

**Idempotent `status:` labels.** Treat `status:*` as a single-valued label
namespace: when setting one, remove the others. On the `glab api` rung use the issue
update endpoint with `add_labels=` / `remove_labels=` (comma-separated); on raw REST
`PUT /projects/:id/issues/:iid?add_labels=status:in-review&remove_labels=status:in-progress`.
Pre-create the `status:*` label set once at config time (`POST /projects/:id/labels`,
tolerate the already-exists error) or tolerate label-create-on-demand — GitLab
**auto-creates** unknown labels named on issue create/update, so an explicit
pre-create is belt-and-suspenders, not required.

### Readiness label (`tracker.readyState` — fn-58 R3/R4)

GitLab has no workflow states, so the readiness signal resolves to a **label**:
`tracker.readyState` holds a label name. **Pre-create-and-confirm ceremony parity**
(mirrors github.md / steps.md Phase 1): the ceremony pre-creates the readiness label
(`POST /projects/:id/labels`) and writes the config **only once the label is
confirmed to exist** — it tolerates the **already-exists** error (HTTP 409 / "label
already exists") as idempotent but surfaces any **other** create failure instead of
writing the config, so the ceremony never manufactures the stale-config warn/noop
below. Read-side semantics ([status-sync.md](status-sync.md) § Readiness projection
owns the procedure):

- **Label present on the issue ⇒ local `ready=true`; label ABSENT ⇒ `ready=false`**
 — absence is a *normal* state (un-labeling IS how a GitLab user un-readies a
 spec), never an error and never a warn/noop.
- Only an **unresolvable config** warns: the configured label missing from the
 *project's* label namespace (`GET /projects/:id/labels?search=<readyState>` —
 compare names case-insensitively for the exact match) ⇒ warn `noop` receipt, flag
 untouched, sync continues.
- **One-way pull:** the adapter never adds/removes the readiness label from the flow
 side — readiness is projected tracker → local only, and it is independent of the
 single-valued `status:*` namespace above (a `ready` label coexists with any
 `status:<x>` label).

## Normalized mapping — the firewall

The `glab`/REST JSON wire shape maps **to/from** the normalized structs in
[adapter-interface.md](adapter-interface.md) (`issue` / `comment` /
`status {raw, normalized}`) **at the adapter boundary**. Reconcile (fn-52.4/.5) only
ever sees the normalized form — a transport bug stays in this file; a merge bug
stays in reconcile.

| normalized `issue` field | GitLab source (`GET /projects/:id/issues/:iid` JSON) | Notes |
|---|---|---|
| `id` | **`id`** (global issue id — immutable, project-independent) | **durable dedupe key** — stored via `sync set-tracker-id`. Never the `iid`. |
| `identifier` | `"<project>#" + iid` (e.g. `group/project#12`) | display only; `iid` is project-local; surfaced in listings. |
| `title` | `title` | |
| `body` | `description` | free-form GitLab-Flavored Markdown. |
| `status.raw` | `state` (+ `status:` label) | the literal GitLab signal (`opened`/`closed`). |
| `status.normalized` | the read-mapping table above | reduced-fidelity recovery via `status:` label. |
| `priority` | (none native) — a `priority:*` label if the project uses one | folded, never auto-changed (R7). |
| `labels` | `labels[]` (array of strings on read) | includes the `flow:<id>` back-reference label AND the `status:*` label. |
| `url` | `web_url` | |
| `updatedAt` | `updated_at` | drives staleness + echo-suppression. |

`tracker`/`type` on the struct are set to `"gitlab"` / `"issue"`.

### `authorAuthority` — from project membership `access_level` (fn-68 R15 security)

Populate the `comment.authorAuthority` tier (the answer-valve authorization gate)
from the comment author's **project membership `access_level`** (`GET
/projects/:id/members/all/:user_id` → `access_level`) — the GitLab analog of GitHub
`author_association` / Jira `accountType`:

- **`access_level` ≥ 30 (Developer / Maintainer / Owner)** ⇒ **`writer`**.
- **`access_level` < 30 (Reporter 20 / Guest 10) or no membership** ⇒ **`outsider`**.
- **bot / service account** (a `*-bot` / service-account user, or the CI job token's
 bot identity) ⇒ **`bot`**.
- **unknown / unresolvable** ⇒ **`unknown`** — **fail closed** (treated as NOT
 authorized; the answer valve honors a `flow-next:answer` marker ONLY from a
 `writer`).

`/members/all/` (not `/members/`) is used because it includes **inherited** group
membership — a user who is a Developer on the parent group but not directly on the
project still resolves as a `writer`.

## The core interface methods over `glab` / REST

The original **six** core methods (`fetchIssue` / `writeIssue` / `listComments` /
`postComment` / `readStatus` / `setStatus`) **plus the enumeration method**
`listOpenIssues` (fn-68). The dependency-projection pair (`listIssueRelations` /
`setIssueRelation`, fn-64) is its own section below — together these are the
**nine-method** interface ([adapter-interface.md](adapter-interface.md)). Mapping
wire ↔ normalized happens here, at the adapter boundary; reconcile never sees a
GitLab JSON shape.

> **Invocation convention for this section.** Examples use the **`glab api`** rung
> (the primary). `$ENC` = `encodedProject` (the URL-encoded `tracker.perTracker.project`);
> `$IID` = the project-local issue number; `$ID` = the global issue id (storage/dedup
> only). On the **raw-REST rung**, run the identical relative path against
> `<host>/api/v4/` with the [header ladder](#header-ladder-raw-rest-rung-only)
> (`PRIVATE-TOKEN` or `JOB-TOKEN`); the path strings are the same.

### `fetchIssue(trackerId)` → normalized `issue` | not-found

```bash
glab api "projects/$ENC/issues/$IID"
# → JSON with id, iid, title, description, state, labels, web_url, updated_at, author
```
- Map per the firewall table above. `state` + the `status:` label → `status`.
- **not-found:** a deleted/moved/404 issue makes `glab api` **exit non-zero** with a
 `404 {"message":"404 Not found"}` on stderr ⇒ return `not-found` — **never raise
 out of the adapter**. The skeleton then emits an `errored` receipt + prompts/queues
 unlink (see the error contract below).

### `writeIssue(issue)` → `{id, identifier, url}` (upsert)

```bash
# CREATE (no issue.id) — body via stdin/--body-file to dodge shell quoting.
# `glab issue create` works, but to capture the global id in one shape use glab api:
URL=$(printf '%s' "$BODY" | glab api --method POST "projects/$ENC/issues" \
 --field "title=$TITLE" --field "description=@-" \
 --field "labels=flow:$FLOW_ID,status:$NORMALIZED_STATUS" \
 --jq '.web_url')
# Re-fetch (or capture the same POST response) for the global id + iid:
glab api "projects/$ENC/issues/$NEW_IID" --jq '{id, iid, web_url}'

# UPDATE (issue.id present) — the path takes the iid.
# PRESERVE the flow-owned <!-- flow:deps -->…<!-- /flow:deps --> region: $BODY is the
# rendered spec body (renderFlowToTracker), which never contains the dep block — a raw
# full-body replace would WIPE it, and the next projectDepRelations would misread the
# ledgered edge as remotely-removed → false collision (self-deletes projected deps).
# Read the current description, carry its fenced block forward, THEN update:
CURRENT=$(glab api "projects/$ENC/issues/$IID" --jq '.description')
DEPS_BLOCK=$(printf '%s' "$CURRENT" | sed -n '/<!-- flow:deps -->/,/<!-- \/flow:deps -->/p')
BODY_WITH_DEPS="$BODY"
[ -n "$DEPS_BLOCK" ] && BODY_WITH_DEPS=$(printf '%s\n\n%s' "$BODY" "$DEPS_BLOCK")
printf '%s' "$BODY_WITH_DEPS" | glab api --method PUT "projects/$ENC/issues/$IID" \
 --field "title=$TITLE" --field "description=@-"
```
- **Preserve the `<!-- flow:deps -->` fenced region on every UPDATE.** This is the
 WRITE half of the `trackerBodyForMerge` ownership model ([body-merge.md](body-merge.md)
 § Step 0.5): the merge strips the block at the hash boundary; the write must RETAIN
 it. Carry the existing block forward verbatim (idempotent — a later
 `setIssueRelation` edits *only inside* the markers). `renderFlowToTracker` never
 emits the block, so a naive full-`description` replace self-deletes a normal push's
 projected deps and contradicts body-merge.md's "render never overwrites it"
 invariant. (Identical concern to github.md; GitLab native links — when licensed —
 live off-body and need no carry-forward, but the `<!-- flow:deps -->` block is the
 durable direction source on every tier, so always carry it.)
- **Upsert by presence of `issue.id`** (interface rule): no id ⇒ create; id ⇒ update.
- After a **create**, capture both the global `id` (durable dedupe key) and the
 `iid` (display); return `{ id (global id), identifier ("<project>#"+iid), url
 (web_url) }`.
- Write the flow back-reference on create/first-link: a **`flow:<id>` label** (single
 colon — see § Identity) plus the initial `status:<normalized>` label, so the issue
 points back at the spec.
- **`description=@-`** reads the body from stdin (the glab/curl `@-` field convention)
 — the GitLab analog of github.md's `--body-file -`. Never inline a markdown body
 as a shell argument.

### `setStatus(trackerId, status)` → ok | errored

Apply the write-mapping table above:

```bash
case "$NORMALIZED" in
 done|verified)
 glab api --method PUT "projects/$ENC/issues/$IID" \
 --field "add_labels=status:$NORMALIZED" --field "remove_labels=$OTHER_STATUS_LABELS"
 glab api --method PUT "projects/$ENC/issues/$IID" --field "state_event=close" ;;
 backlog|planned|in-progress|in-review)
 glab api --method PUT "projects/$ENC/issues/$IID" --field "state_event=reopen" # no-op if already opened
 glab api --method PUT "projects/$ENC/issues/$IID" \
 --field "add_labels=status:$NORMALIZED" --field "remove_labels=$OTHER_STATUS_LABELS" ;;
 deferred|wontfix)
 : ;; # R7: surface to the user / queue — NEVER auto-close unilaterally
esac
```
- A non-zero exit (bad iid, perms, label error) ⇒ return `errored` (don't crash);
 the skeleton writes an `errored` receipt and does not advance state.
- **`CI_JOB_TOKEN` write 403** ⇒ degrade to the **no-op rung + receipt note** (R2),
 not `errored` — the token simply lacks write scope for this project.
- `remove_labels=$OTHER_STATUS_LABELS` keeps the `status:*` namespace single-valued
 (list every `status:*` not being set).

### `listComments(trackerId)` → normalized `comment[]`

```bash
glab api "projects/$ENC/issues/$IID/notes" --paginate \
 --jq '.[] | select(.system == false)
 | {id, author: .author.username, authorUserId: .author.id, body, createdAt: .created_at, url: .web_url}'
```
- **MUST filter `system==true` notes** (verified): `GET /issues/:iid/notes` items
 carry `system: true|false`; `system==true` are GitLab **automated events** (label
 changes, state changes, assignment, …) — only `system==false` are human comments.
 Importing `system` notes would flood `## Sync Log` with machine noise.
- **GitLab note ids are stable** (the integer note `id`) — safe as the dedup key.
- **`authorAuthority`** (fn-68 R15 security — populate it here, the producer): resolve
 the author's project `access_level` (`GET /projects/:id/members/all/<author.id>`)
 per § `authorAuthority` — `≥30 ⇒ writer`, `<30/none ⇒ outsider`, bot/service ⇒
 `bot`, unresolvable ⇒ `unknown` (fail closed). (Batch the member lookups per run /
 cache by user id — the notes list often repeats authors.)
- Map each: `author.username`→`author`; `body`, `created_at`→`createdAt`; **detect
 the flow-owned marker set** in `body` → set `marker` (flow's own echo, skipped on
 pull). The set is closed (fn-68 R15): `flow-next:sync`→`flow-evt:<event>`,
 `flow-next:question`→`flow-evt:question`, rolling `flow-next:status`→`flow-evt:status`
 ([adapter-interface.md](adapter-interface.md) § `comment` marker-vocabulary table).
 **`flow-next:answer` is the human reply — `marker` stays `null`, but surface its
 `id`** (the round-trip claims it by `id`). Genuine tracker-side comments get
 `marker:null` and pull into the spec sync log.
- **`comment.parentId` is always `null` on GitLab (fn-68 R15).** GitLab issue notes
 are **flat — there is no threading / parent link on a top-level issue note**, so
 the question-valve answer round-trip CANNOT match an answer to its question by
 thread. The load-bearing match is the body marker: a human's answer note carries
 `<!-- flow-next:answer id=<hash> -->`, matched to the open question **by `id`,
 threading-blind** ([adapter-interface.md](adapter-interface.md) § `comment`;
 [steps.md](../steps.md) Phase 7). Same flat-tracker posture as GitHub.
- **Bounded pagination (mandatory).** GitLab notes are paginated. Use `glab api
 --paginate` (or raw REST `?per_page=100` + `page=`) with an **explicit max page
 bound** — and a **receipt note if the bound truncates** the read. Never silently
 under-read comments.

### `postComment(trackerId, body)` → normalized `comment`

```bash
printf '%s' "$BODY_WITH_MARKER" | glab api --method POST \
 "projects/$ENC/issues/$IID/notes" --field "body=@-" --jq '{id, web_url}'
```
- `$BODY_WITH_MARKER` carries the `flow-evt:<event>` marker line (echo suppression +
 dedup, per [comments-sync.md](comments-sync.md)).
- The POST returns the new note's `id` + `web_url` directly — no re-list needed to
 recover the id (unlike GitHub's create). Return the normalized `comment`.
- **`body=@-`** reads the body from stdin (never an inline markdown argument).

### `readStatus(trackerId)` → normalized `status`

Derived from the `fetchIssue` `state` + `status:` label — no separate call (same as
GitHub deriving status from `state`+`stateReason`+label, and Linear from
`state{name type}`).

### `listOpenIssues(filter) → issue[]` (fn-68 — enumeration)

Enumerate the **promoted lane** — opened issues carrying the **exact**
`tracker.readyState` **label** (GitLab has no workflow states; readiness is a label,
[Readiness label](#readiness-label-trackerreadystate--fn-58-r3r4)). The `labels`
filter is **exact** (AND-combined if multiple) — there is no label *ordering*, so no
"and-later" lane exists (adapter-interface.md § Enumeration transport).

```bash
glab api "projects/$ENC/issues?state=opened&labels=$READY_LABEL&per_page=100" --paginate \
 --jq '.[] | {id, iid, title, description, state, labels, web_url, updated_at, author}'
```

- **`labels=$READY_LABEL`** is the exact promoted-lane filter — only issues carrying
 the configured `tracker.readyState` label, never "beyond" it.
- **`state=opened`** bounds it to opened issues — never the whole (closed-inclusive)
 history.
- **Map each into the normalized `issue` struct** via the same firewall table
 `fetchIssue` uses (§ Normalized mapping — global `id`→`id`, `"<project>#"+iid`→
 `identifier`, `state`/`status:` label→`status`, `labels`→`labels`, …). A
 tracker-only ticket (no linked flow spec) maps identically. **Linkage is decided
 authoritatively by the local sync state** (the recorded linked tracker-ids), NOT by
 `flow:<id>` label absence — the label is a corroborating hint only, and a label set
 that lost the back-reference is never read as "unlinked" (a linked issue is never
 mis-classified tracker-only).
- **Bounded pagination (mandatory).** As with `listComments`, page with
 `--paginate` / `per_page=100` under an explicit max bound; a truncating bound
 writes a **receipt note**. Never silently under-read the promoted lane.
- **`tracker.readyState` unset ⇒ the skill never calls this** (steps.md Phase 7a
 short-circuits to a `noop` + note — there is no label to filter on); reached with
 an empty label it returns `[]` + `noop`. `TRANSPORT=none` (no glab credential and
 no env token) ⇒ `noop` + receipt note, `[]` — same no-transport floor as the other
 methods.

## Relation transport (dependency projection, fn-64)

The `listIssueRelations` / `setIssueRelation` pair ([adapter-interface.md](adapter-interface.md)
§ Relation transport) projects a Flow `depends_on_epics` edge as a **blocked-by**
relation via GitLab **native issue links** — `glab api
projects/:id/issues/:iid/links` (the `glab issue` subcommand has **no** link command
— verified) or raw REST `POST /projects/:id/issues/:iid/links`. GitLab has **two**
fidelities, selected by a **license probe** — the same reduced-fidelity posture this
adapter takes for status:

| Path | Transport | Use when | Fidelity |
|------|-----------|----------|----------|
| **Native directional** | `POST …/issues/:iid/links` `link_type=is_blocked_by` (+ always the `<!-- flow:deps -->` block) | the namespace is **Premium/Ultimate-licensed** (the POST returns 201) | first-class, board-visible directional "Blocked by" + `blocking_issues_count` |
| **Degraded** | `POST …/links` `link_type=relates_to` (directionless, UI-only) **AND always** the `<!-- flow:deps -->` body block | the directional POST returns **403 `Blocked issues not available for current license`** (Free namespace OR personal-namespace project) | `relates_to` gives GitLab-UI visibility only; **direction + provenance live in the body block** |
| **no-op** | none + `noop` receipt | `TRANSPORT=none` (no glab credential / no env token) | nothing written |

The **direction convention is anchored once** in adapter-interface.md — *the current
issue (A) is blocked by the dependency issue (B)*; the native directional link and
the `<!-- flow:deps -->` block both point A's "blocked by" at B, never inverted. A
directionless `relates_to` carries **no** direction, which is exactly why it is
never read back as a relation (below).

### Native facts (pin these — verified live 2026-06-28)

- **`is_blocked_by`/`blocks` are PREMIUM; the license is PER-NAMESPACE.** `POST
 /projects/:id/issues/:iid/links` with `link_type=is_blocked_by`:
 - **403 `Blocked issues not available for current license`** on a **Free**
 namespace AND on a **personal-namespace** project — *even when the account holds
 an Ultimate trial on a different group*, because the license is **per-namespace**
 (a personal project never inherits a group's Premium/Ultimate trial).
 - **Works (HTTP 201) in a Premium/Ultimate-licensed GROUP project** — verified
 directional: `link_type=blocks` makes the dependent show `is_blocked_by` and
 increments the blocker's `blocking_issues_count`.
 - **`link_type=relates_to` works on ALL tiers (HTTP 201) but is DIRECTIONLESS.**
- **The degrade ladder covers both WITHOUT pre-detecting the license** — try the
 directional `is_blocked_by` first; on the license **403**, degrade. Do **not**
 probe `GET /namespaces` / license state up front; the 403 is the signal.
- **`POST …/links` body keys:** `target_project_id` (the **numeric** project id of
 the blocker's project) + `target_issue_iid` (the blocker's iid) + `link_type`. The
 endpoint path takes the **blocked** issue A's `iid`; the body names the **blocker**
 B. The link `id` returned is the link record, not an issue id.
- **DELETE (`DELETE …/issues/:iid/links/:link_id`) is OPTIONAL / future**, not
 implemented here (default-safe no-delete; never removes a remote relation — R6).

### License degrade (probe-by-attempt, don't pre-detect)

```bash
# A = the blocked issue (path iid), B = the blocker. Try directional first:
if glab api --method POST "projects/$ENC/issues/$A_IID/links" \
 --field "target_project_id=$B_PROJECT_NUM" \
 --field "target_issue_iid=$B_IID" \
 --field "link_type=is_blocked_by" >/dev/null 2>&1; then
 REL_PATH=native # 201 → Premium/Ultimate namespace; directional link created
else
 REL_PATH=degraded # 403 license → relates_to (UI only) + the body block carries direction
fi
# When TRANSPORT=none the POST never runs → no-op rung.
```

A **201** selects the native directional path; the license **403** selects the
degraded path. Cache the verdict for the run. (Other non-zero exits — bad iid,
perms — return `errored`, not a silent degrade.)

### `listIssueRelations(issue)` → normalized `relation[]`

**Native (Premium/Ultimate):**
```bash
glab api "projects/$ENC/issues/$IID/links" \
 --jq '.[] | select(.link_type == "is_blocked_by") | {iid, id, project_id}'
```
Each `is_blocked_by` link → one `relation`: `{ from: "<project>#"+A.iid (blocked),
to: "<project>#"+blocker.iid (blocking), type: "blocks", source: "unknown" }`. Native
links store no flow authorship, so `source` is `unknown` and the flow-side
`depRelations` ledger (fn-64.1) is the provenance authority (R6/R7) — same as the
GitHub-native + Linear-native rungs.

**Degraded / always — the `<!-- flow:deps -->` block:** parse the `#N` / `<project>#N`
lines **inside** the `<!-- flow:deps -->` … `<!-- /flow:deps -->` markers of the
issue `description` (`glab api "projects/$ENC/issues/$IID" --jq '.description'`). Each
ref inside the markers → `{ from: "<project>#"+A.iid, to: <ref>, type: "blocks",
source: "flow" }` (inside the fence ⇒ provably ours). Refs **outside** the markers
are NOT relations — never returned.

> **NEVER read a relation from a directionless `relates_to` link.** A `relates_to`
> link carries **no** from/to direction, so `listIssueRelations` returns directed
> `{from, to, type:"blocks"}` relations **ONLY** from native **directional** links
> (`is_blocked_by`) **or** the flow-owned `<!-- flow:deps -->` block — **never** from
> a `relates_to`. The block is the durable direction/provenance source on a degraded
> (Free / personal) namespace; the `relates_to` link is GitLab-UI decoration only.

### `setIssueRelation(issue=A, blockedBy=B)` → ok | errored | noop

**Read-before-write (mandatory, R3):** `listIssueRelations(A)` first; skip the write
when A-is-blocked-by-B already exists (in a native directional link or the
`<!-- flow:deps -->` block). GitLab does not reliably no-op a duplicate link.

**The write (degrade ladder — always also the body block):**
```bash
# 1. Try the native DIRECTIONAL link (per the license-degrade probe above).
# 201 → native path done. 403 license → fall through to relates_to.
glab api --method POST "projects/$ENC/issues/$A_IID/links" \
 --field "target_project_id=$B_PROJECT_NUM" --field "target_issue_iid=$B_IID" \
 --field "link_type=is_blocked_by" \
 || glab api --method POST "projects/$ENC/issues/$A_IID/links" \
 --field "target_project_id=$B_PROJECT_NUM" --field "target_issue_iid=$B_IID" \
 --field "link_type=relates_to" # directionless UI visibility ONLY

# 2. ALWAYS write/update the <!-- flow:deps --> block in A's description for
# DIRECTION + PROVENANCE — on BOTH the native and degraded paths. On native it
# is the provenance ledger's body twin; on degraded it is the ONLY direction
# source (relates_to has none). Rewrite ONLY inside the markers, idempotently:
```
```markdown
<!-- flow:deps -->
**Blocked by:** group/project#12, group/project#15
<!-- /flow:deps -->
```
- **Always write/update the `<!-- flow:deps -->` block** — on native it mirrors the
 native directional link (and is the body-merge-excluded provenance twin); on
 degraded it is the **sole** carrier of direction (since `relates_to` is
 directionless). This is why the block is written on *every* path, not just the
 fallback.
- If the markers are absent, append a fresh empty block to the description (the only
 edit outside the markers — establishing the fence — never touches existing body
 text). Inside the markers: add the `<project>#<iid>` ref only when not already
 present (dedup on the ref token, not a substring). A re-run appends nothing (R3).
- Write the merged `description` back via `glab api --method PUT
 "projects/$ENC/issues/$A_IID" --field "description=@-"` (never an inline body — the
 body-quoting rule above). The block is excluded from body-merge divergence
 detection (fn-64.5 owns the exclusion) so reconcile never folds flow's own block
 back into the spec.
- A `relates_to` link `id` (degraded path) is recorded for idempotency, but
 **provenance/direction never derive from it** — only the ledger + the block.

**Never-delete-non-ours (R6):** `setIssueRelation` only ever **ADDS** the blocked-by
edge — on every path. Native: provenance is the ledger; a native link not in the
ledger is not ours, left alone. Block: only refs inside the fence are ours; a `#N` a
human wrote elsewhere in the description is never touched. `relates_to`: additive
only, never removed.

**Completed-blocker (R5).** A dependency whose issue is closed/done stays a visible
blocked-by relation on every path — the native link is left in place (a closed
blocker still renders) and the fenced ref is not stripped. The adapter never decides
this; the completed-blocker call is the skill's (fn-64.5), keyed off the **local**
dep-spec status (`dep_status` from `flowctl sync list-dep-relations`), and it must
not feed back into `ready=true` gating. The relation is historical/audit, not a
re-gate.

**Identifier parsing.** The block writer/reader accepts the `<project>#<iid>`,
`group/subgroup/project#<iid>` (nested), and bare `#<iid>` forms when matching an
existing entry (the same widening fn-69.1 applied to the `set-tracker-id` identifier
validator); it always *writes* the canonical `<project>#<iid>` form. Cross-project
refs are tolerated on read; native directional links are cross-project-capable
(`target_project_id`), so a degraded-path body ref can name another project's issue.

## `makePr` — link the MR/PR to the issue (native GitLab cross-reference)

When the tracker is **GitLab**, the spec maps to a GitLab *issue* and linkage is
**native GitLab cross-referencing** — no Linear attachment, no Linear Diffs (GitLab
has its own MR review UI). make-pr §4.6a's Linear branch is GitLab-typed-skipped;
instead the GitLab adapter posts a **note** on the issue carrying the PR/MR URL
(verified: a note with the URL renders as a GFM cross-reference). It must be a
**non-closing** reference — flow-next owns the terminal `Done` transition via the
merge-evidence-gated `land.merged` lifecycle (R7/R10), so do **NOT** put a `Closes
#N` in the MR description (that auto-closes the issue on merge and bypasses
flow-next's Done projection). A plain note with the URL gives the cross-link without
hijacking the lifecycle. Gate is the same as the other adapters: bridge **active AND
tracker.type == gitlab** — no separate `makePr` opt-in. (Native MR↔issue auto-link
exists via the MR description, but flow projects a GitHub PR or GitLab MR URL as a
note to stay non-closing.)

## Capability parity (GitLab ↔ GitHub) — the R13 guarantee

Reconcile is genuinely transport-blind only if the GitLab adapter produces the
**same normalized structs** the GitHub adapter does, for every interface method.
Verify per method:

| Interface method | GitLab (`glab`/REST) | GitHub ([github.md](github.md)) | Parity target |
|---|---|---|---|
| `fetchIssue` | `glab api projects/:id/issues/:iid` | `gh issue view --json …` | same `issue` struct (title/body/status/priority/labels/url/updatedAt) |
| `writeIssue` (upsert) | `glab api POST/PUT …/issues` | `gh issue create` / `gh issue edit` | same `{id, identifier, url}` |
| `listComments` | `glab api …/notes` (filter `system==true`) | `gh issue view --json comments` | same `comment[]` (author/body/createdAt/marker); `parentId` always `null` (flat) — answer matched by body `id` marker |
| `postComment` | `glab api POST …/notes` (`body=@-`) | `gh issue comment --body-file -` | same `comment` |
| `readStatus` | from `state`+`status:` label | from `state`+`stateReason`+`status:` label | same `status{raw,normalized}` |
| `setStatus` | `PUT {state_event}` + `status:` label | `gh issue close/reopen` + `status:` label | ok / `errored` |
| `listIssueRelations` | native `is_blocked_by` links (degraded → `<!-- flow:deps -->` block; never `relates_to`) | native `…/dependencies/blocked_by` (reduced → fenced `#N` block) | same blocked-by `relation[]` (`{from,to,type:"blocks",source}`) |
| `setIssueRelation` | native `is_blocked_by` POST (degraded → `relates_to` + body block) | native POST `blocked_by` (reduced → fenced-block append) | ok / `errored` / `noop`; read-before-write on both |
| `listOpenIssues` (fn-68) | `…/issues?state=opened&labels=readyState` | `gh issue list --state open --label readyState` | same `issue[]` at the **exact** readyState lane (label — both exact, no ordering) |
| status map | opened/closed + `status:` label (reduced — recovered via label) | open/closed + reason + `status:` label (reduced) | same **normalized** vocabulary out |

The fidelity gap (GitLab's two-value native state) is bridged by the `status:` label
so the **normalized output is identical** — that is what makes reconcile
transport-blind despite GitLab's poorer native model. If a `status:` label is absent
(human-edited issue), the read-mapping table degrades gracefully to a best-effort
normalized value; that is a documented reduced-fidelity case, not a parity break.

The same holds for relations: a native `is_blocked_by` link and the `<!-- flow:deps
-->` block both produce the **identical** normalized `relation[]`
(`{from,to,type:"blocks",source}`), so the skill (fn-64.5) sees one transport-blind
hook regardless of which GitLab path served it — only the `source` field differs
(`unknown` on native, deferring to the ledger; `flow` inside the block). The
directionless `relates_to` is the one link kind that is **never** read as a relation
(it has no direction) — it is UI decoration, not a parity participant. Native vs
degraded is a fidelity selection, not a parity break.

## Transport-blind proof / round-trip spike — run FIRST

The R13 guarantee: **the same reconcile path over `glab` fixtures yields merge
output identical to the GitHub/Linear path.** Two checks:

### A. Round-trip spike (transport in isolation — no merge)

Push a flow body to a real GitLab issue, then pull it back — format translation
only. Surfaces transport bugs (auth, `description=@-` escaping, iid-vs-global-id,
project encoding, GFM round-trip) BEFORE relying on reconcile.

> **Live-verification status.** The endpoints/limits below were **smoke-tested live
> 2026-06-28** against gitlab.com (throwaway project `gmickel/fnsmoke`, permanently
> deleted after) — create/read/update/close, GFM body, labels (incl. a `flow:<id>`
> back-ref), `listOpenIssues` by label, notes, MR-link note, and the Premium-403
> relation degrade. A *fresh* round-trip needs a real `GITLAB_TOKEN` against a
> project with issue write access; the `glab`/REST flags + JSON fields it depends on
> are verified and pinned above. Run it once per environment.

Fixture (the same canonical flow body the GitHub/Linear spikes use — headings, a
checklist, a fenced block, a link — the structures most likely to be mangled):

~~~markdown
## Goal
Round-trip fixture for the GitLab transport spike.

## Acceptance
- [ ] item one
- [x] item two (done)

## Notes
A fenced block:

```
exact text — must survive verbatim
```

A [link](https://example.com) and an inline `code` span.
~~~

Steps:

1. **Build the body** — write the fixture to `/tmp/spike-flow-body.md`.
2. **Push (create)** via `writeIssue` (no id ⇒ create), body via stdin:
 ```bash
 IID=$(printf '%s' "$(cat /tmp/spike-flow-body.md)" | glab api --method POST \
 "projects/$ENC/issues" --field "title=flow spike" --field "description=@-" \
 --jq '.iid')
 ```
3. **Pull back** via `fetchIssue(iid)`:
 ```bash
 glab api "projects/$ENC/issues/$IID" --jq '.description' > /tmp/spike-pulled-body.md
 ```
4. **Oracle (success/fail):**
 ```bash
 if diff -u /tmp/spike-flow-body.md /tmp/spike-pulled-body.md; then
 echo "SPIKE PASS — round-trip preserved the body"
 else
 echo "SPIKE FAIL — glab transport mangled the body; see diff above"
 fi
 ```
 A non-empty diff is a transport bug to fix here BEFORE relying on reconcile —
 e.g. GitLab normalizing trailing whitespace or line endings. (If GitLab
 canonicalizes GFM in a stable, loss-less way, record that exact canonical form as
 the fixture's expected output so reconcile reconciles against *that*.)
5. **Cleanup:** `glab api --method PUT "projects/$ENC/issues/$IID" --field
 "state_event=close"` (or delete via `glab api --method DELETE
 "projects/$ENC/issues/$IID"` where the token allows).

The spike writes a receipt like any sync run:
`sync receipt <spec> --status noop --transport glab --note "round-trip spike: PASS|FAIL"`
(status `noop` — a transport probe, not a sync of a tracked spec; no `--event` — the
spike is a manual diagnostic, never a lifecycle touchpoint).

### B. Cross-tracker reconcile parity (the actual R13 check)

Feed the **same normalized fixtures** through reconcile twice — once with the GitLab
adapter's output structs, once with the GitHub adapter's — and assert the merge
output is identical:

```bash
# Pseudo-procedure (reconcile is agentic — fn-52.4/.5 — and consumes structs):
# 1. Take a flow body + a base snapshot + a tracker-side edit.
# 2. Produce the normalized `issue`/`comment`/`status` structs TWICE:
# - via the GitLab mapping tables above (opened/closed + status: label)
# - via the GitHub mapping (open/closed + reason + status: label)
# Construct both so they represent the SAME logical state (e.g. GitLab
# opened+`status:in-progress` ≡ GitHub OPEN+`status:in-progress`).
# 3. Run the UNCHANGED reconcile core (body-merge.md / status-sync.md /
# comments-sync.md) on each struct set against the same base.
# 4. Oracle: the two merge outputs are identical (same merged body, same
# who-wins status, same comment dedup). Any difference is a mapping bug in an
# adapter — NOT a reconcile change. Reconcile is never edited to make a
# transport pass.
```

This is the load-bearing R13 assertion: identical reconcile output across GitLab and
GitHub fixtures, with the reconcile core touched in neither task.

## Error contract — never crash, never corrupt state

The adapter honors the [adapter-interface.md](adapter-interface.md) contract rules.
The failure modes that MUST be non-destructive:

- **Missing / deleted / moved / 404 linked issue** — `glab api` exits non-zero (`404
 Not found`). `fetchIssue` returns `not-found` (NEVER raises). The skeleton then:
 - emits `sync receipt … --status errored --transport glab|rest ${EVENT:+--event "$EVENT"}`,
 - does **NOT** crash, does **NOT** clear state, does **NOT** advance `lastSyncedAt`
 (a failed fetch must never corrupt the merge base),
 - prompts the user to unlink (interactive) or queues an unlink decision (`sync
 defer`, Ralph) — never a silent `sync clear`.
- **Unauthenticated mid-run** (`GITLAB_TOKEN` expired/revoked) — `glab`/`curl` exit
 with a 401. Treat as the **no-op rung** for that operation: `noop` receipt + note,
 no state write — same as never having had a transport.
- **Scope 403** (`insufficient_granular_scope`) — surface GitLab's message
 **verbatim** so the user knows exactly which project permission to grant; the
 operation is `errored` (read) or degrades to no-op (a `CI_JOB_TOKEN` write 403),
 never a crash.
- **Rate limit** — GitLab returns **HTTP 429** with `Retry-After` / `RateLimit-Reset`.
 `glab`/`curl` surface a non-zero exit. **Bounded retry** (exponential, honor the
 reset hint), then **defer + receipt** rather than failing the run.
- **Pagination truncation** — a `listComments` / `listOpenIssues` read that hits the
 explicit page bound writes a **receipt note** (under-read is surfaced, never
 silent).
- **Batch sync is item-level** — one spec's `errored`/rate-limit does not abort the
 batch: that spec gets its own `errored` receipt + no state write, and the run
 continues to the next spec.
- **Echo suppression** — after a push, the resulting tracker-side body hash is
 recorded (rides on the merge-base snapshot, fn-52.4); the next pull's matching hash
 ⇒ flow's own echo ⇒ `noop`, never a phantom conflict. `updated_at` from the JSON
 helps distinguish a real GitLab-side edit from an echo. Comment echo uses the
 `flow-evt:<event>` marker (above), same as GitHub.

## Boundaries

- **This is the transport, not the merge.** The adapter maps `glab`/REST JSON ↔
 normalized and routes the `glab → rest → no-op` ladder. The 3-way body merge
 ([body-merge.md](body-merge.md), fn-52.4), the status who-wins
 ([status-sync.md](status-sync.md), fn-52.5), and the comments/evidence append +
 dedup ([comments-sync.md](comments-sync.md), fn-52.5) consume the normalized
 structs and live in those tasks — **reused unchanged** here.
- **Reduced fidelity is by design.** GitLab's two-value native state cannot match
 Linear's workflow taxonomy; the `status:` label bridges it so the *normalized*
 output is identical. Document the gap (above); do not invent a richer GitLab state
 model.
- **Relations are reduced on Free/personal namespaces by design.** Directional
 blocked-by needs a Premium/Ultimate-licensed namespace; the `relates_to` + `<!--
 flow:deps -->` block degrade is the honest floor (UI visibility + body-block
 direction), not a fabricated directional link. Record reduced fidelity on the
 receipt.
- **No MCP rung — by decision.** The official GitLab MCP exists (Premium/Ultimate +
 OAuth) but is deliberately not wired; `glab` + token is the universal zero-setup
 floor (noted available-but-not-wired above).
- **No new hard dependency.** `glab` is not required (the raw-REST rung needs only an
 env token; the terminal rung is a documented no-op). The zero-dep base install is
 untouched (spec Boundaries / STRATEGY opt-in carve-out).
- **One GitLab project per linked spec** (`tracker.perTracker.project`) — the bridge
 config resolves a single group/project path per repo, mirroring the one-repo
 GitHub / one-team Linear constraint.
