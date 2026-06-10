# GitHub adapter — transport via `gh` (headless-safe, reduced-fidelity status)

The GitHub implementation of the six-method transport interface
([adapter-interface.md](adapter-interface.md)). GitHub-next per the staging
decision (Linear first — [linear-ladder.md](linear-ladder.md) — GitHub second,
the **headless-robust** path). This is the transport behind the fn-52.2 adapter
interface; it reuses the fn-52.4/.5 reconcile core **unchanged** — proving the
reconciliation is transport-blind (the R13 guarantee). It mirrors the Linear
adapter's shape, but GitHub has **one** transport (`gh`), so there is no
multi-rung ladder — only a single rung plus the terminal no-op.

| Rung | Transport | Use when | Notes |
|------|-----------|----------|-------|
| 1 | **`gh` CLI** (headless via `GH_TOKEN`) | `gh auth status` exits 0 (a token is reachable) | the only GitHub transport; scriptable, version-stable JSON |
| 2 (terminal) | **no-op + receipt note** | `gh` not installed OR `gh auth status` non-zero | the bridge is configured but no GitHub transport is reachable |

The chosen rung is recorded on every receipt: `sync receipt … --transport gh|none`
— plus, on a lifecycle run, the touchpoint it served: `${EVENT:+--event "$EVENT"}`
(`$EVENT` is set in steps.md Phase 0; empty on manual runs, so the flag is omitted).
The agentic reconciliation (fn-52.4 body merge, fn-52.5 status/comments) is
**identical regardless of tracker** — that is the R13 guarantee, and the parity
check below (vs the Linear adapter) is how it is verified.

> **Why `gh` and not the GraphQL/REST API directly.** `gh` is the headless,
> auth-managed analog of Linear's GraphQL rung: `GH_TOKEN` for non-interactive
> auth, stable `--json` output, no OAuth dance to script. It is the
> headless/CI/Ralph-safe path (GitHub has no MCP-vs-headless split like Linear —
> `gh` covers both interactive and headless), which is why GitHub is the
> headless-robust tracker shipped second.

## Rung detection (probe, don't assume)

Detection lives in the skill (host agent), not in flowctl — same shape as fn-51's
driver ladder and the Linear ladder. Probe; take the rung that passes:

```bash
# Rung 1 — gh reachable + authenticated. `gh auth status` exits 0 when a token
#   (incl. GH_TOKEN) resolves for the host; non-zero when unauthenticated. The
#   discovery probe in SKILL.md uses this same signal.
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  TRANSPORT=gh
fi

# Rung 2 — neither reachable:
#   TRANSPORT=none → every interface method is a documented no-op + receipt note.
TRANSPORT="${TRANSPORT:-none}"
```

Headless usage: set `GH_TOKEN` (a PAT or a CI/`GITHUB_TOKEN`) in the
environment; `gh` is then fully non-interactive — no browser, no prompt. This is
the Ralph/cron/CI path. `gh auth status --json` (gh ≥ 2.x) can confirm the active
account programmatically if a richer probe is wanted, but the exit code is the
load-bearing signal.

## No-op rung (terminal) — never crash

When `TRANSPORT=none`, the configured bridge cannot reach GitHub this run. Every
one of the six interface methods becomes a documented no-op (same fail-soft
contract as the Linear terminal rung and fn-51's manual rung):

- `fetchIssue` / `listComments` / `readStatus` → return nothing actionable
  ("no remote view available this run"); the spec's flow-side state is left
  untouched and the merge base is NOT advanced.
- `writeIssue` / `postComment` / `setStatus` → perform no remote write.
- The run emits `sync receipt … --status noop --transport none ${EVENT:+--event "$EVENT"}
  --note "no GitHub transport reachable (gh not installed or not authenticated; set GH_TOKEN)"`.
- `lastSyncedAt` is never advanced on a no-op (no real reconciliation happened).

## `gh` connection facts (pin these — they have sharp edges)

- **Auth (headless):** `GH_TOKEN` (preferred for non-interactive) or
  `GITHUB_TOKEN` in CI. `gh auth status` exits 0 iff a token resolves; it does
  **not** need `--json` for the probe. Never prompt — a missing token ⇒ the no-op
  rung, not an interactive login.
- **Repo target:** `gh` infers the repo from the cwd's git remote. For an
  out-of-tree repo pass `-R <owner>/<repo>` on every command (the bridge config's
  `tracker.perTracker.repo` supplies it). Pin the repo explicitly in CI where cwd
  may differ.
- **Bodies via `--body-file -`, NEVER raw `--body`.** Markdown bodies contain
  backticks, `$`, newlines, and quotes that break shell quoting on `--body`. Write
  the body to a temp file (or pipe stdin) and use `--body-file -`. This is the
  GitHub analog of "pass bodies as GraphQL variables" on the Linear rung — same
  failure mode (escaping mangles the round-trip), same fix.
- **id vs number:**
  - **Durable dedupe key = the GraphQL node id** (`id`, e.g. `I_kwDO…`) from
    `--json id`. Store it via `sync set-tracker-id` — never the `#123` number.
  - `#123` (`number`) is the display key (the normalized `identifier`); surface it
    to humans. GitHub does not reuse issue numbers within a repo, but the node id
    is still the canonical, transfer-stable key — transferring an issue to another
    repo changes its `number`, not its node id. Keep the node id authoritative,
    consistent with the Linear UUID rule.
  - `gh issue` subcommands accept the **number** (or a URL) as the positional arg;
    the node id is for storage/dedup, not for `gh` command input.
- **State is two-valued + a reason** (the fidelity gap — see below):
  `--json state` → `OPEN` | `CLOSED`; `--json stateReason` →
  `COMPLETED` | `NOT_PLANNED` | `REOPENED` | `null`.
- **Rate limit is request-count (5,000/hr authenticated REST; GraphQL has a
  separate point budget).** Unlike Linear (complexity-based HTTP 400 `RATELIMITED`),
  GitHub returns **HTTP 403 / 429 with `Retry-After` or
  `X-RateLimit-Remaining: 0` + `X-RateLimit-Reset`**. `gh` surfaces this as a
  non-zero exit with the message in stderr. **Back off and retry** (exponential,
  honor `Retry-After`/`X-RateLimit-Reset`) rather than failing the run — same
  non-destructive contract as the Linear rung, different signal.

## State fidelity — reduced vs Linear (the key GitHub difference)

Linear has a rich, team-defined workflow-state taxonomy (5 `state.type`s + named
states). GitHub native state is only **`OPEN`/`CLOSED` + a `stateReason`**. The
flow/Linear normalized vocabulary (`backlog` · `planned` · `in-progress` ·
`in-review` · `done` · `verified` · `deferred` · `wontfix`) is **richer than
GitHub can natively represent**. So the GitHub adapter:

1. **Maps the normalized status DOWN to GitHub's two-value native state + reason**
   (what `setStatus` writes), and
2. **Carries the fine-grained status as a label** (`status:in-progress`,
   `status:in-review`, …) so the full flow status survives a round-trip and
   `readStatus` can recover it.

### Read (`readStatus` / `fetchIssue` → normalized `status`)

Prefer the `status:` label when present (it carries full fidelity); fall back to
native `state` + `stateReason` when no `status:` label exists (e.g. an issue
edited directly on GitHub by a human who didn't touch the label):

| GitHub native (`state` / `stateReason`) | `status:` label present? | normalized | who-wins ([status-sync.md](status-sync.md)) |
|---|---|---|---|
| `OPEN` | `status:<x>` | use the label's `<x>` (`in-progress` / `in-review` / `planned` / `backlog`) | per fn-52.5 |
| `OPEN` | none | `in-progress` (best-effort default for an open issue) | flow wins |
| `CLOSED` / `COMPLETED` | (label ignored — native is authoritative for closed) | `done` | tracker wins |
| `CLOSED` / `NOT_PLANNED` | — | `wontfix` (or `deferred` via config) — **surface, never auto-apply** | surface to user |
| `CLOSED` / `null` (legacy close) | — | `done` (treat a reasonless close as completed) | tracker wins |

`status.raw` = the literal GitHub signal (e.g. `"CLOSED/NOT_PLANNED"` or the
`status:` label text) for the sync log; `status.normalized` = the table result.

### Write (`setStatus` — map normalized DOWN)

| normalized | GitHub native action | `status:` label |
|---|---|---|
| `backlog` / `planned` / `in-progress` / `in-review` | ensure **OPEN** (`gh issue reopen` if closed) | set `status:<normalized>` (remove any other `status:*`) |
| `done` / `verified` | `gh issue close --reason completed` | set `status:<normalized>` (so `verified` vs `done` is recoverable) |
| `deferred` / `wontfix` | **do NOT auto-apply** — these are R7 surface-only | — |

**`deferred` / `wontfix` are surfaced, never auto-applied** (R7 semantics, same as
Linear's `canceled`-type states): the adapter reports the desired transition to
the user (or queues it in Ralph) rather than closing the issue as `not planned`
unilaterally. A human confirms a `wontfix`/`deferred` close. The mapping ABOVE
that produces them is for the *read* direction (interpreting a human's
GitHub-side close) — only the open/closed-completed transitions are auto-written.

**Idempotent `status:` labels.** Treat `status:*` as a single-valued label
namespace: when setting one, remove the others (`gh issue edit … --add-label
status:in-review --remove-label status:in-progress`). Create the label set once at
config time (`gh label create status:in-progress …` — optional; GitHub auto-allows
unknown labels on `--add-label` only if they already exist, so pre-create them or
tolerate the "label not found" by creating on demand).

### Readiness label (`tracker.readyState` — fn-58 R3/R4)

GitHub has no workflow states, so the readiness signal resolves to a **label**:
`tracker.readyState` holds a label name (the ceremony pre-creates it with the
tolerate-already-exists guard — steps.md Phase 1 step 5; `gh label create` fails
with a 422 when the label exists, which is fine/idempotent). Read-side semantics
([status-sync.md](status-sync.md) § Readiness projection owns the procedure):

- **Label present on the issue ⇒ local `ready=true`; label ABSENT ⇒
  `ready=false`** — absence is a *normal* state (un-labeling IS how a GitHub user
  un-readies a spec), never an error and never a warn/noop.
- Only an **unresolvable config** warns: the configured label missing from the
  *repo's* label namespace (`gh label list -R "$REPO" --search "$READY_LABEL"
  --json name` — substring search, compare names case-insensitively for the exact
  match) ⇒ warn `noop` receipt, flag untouched, sync continues.
- **One-way pull:** the adapter never adds/removes the readiness label from the
  flow side — readiness is projected tracker → local only, and it is independent
  of the single-valued `status:*` namespace above (a `ready` label coexists with
  any `status:<x>` label).

## Normalized mapping — the firewall

The `gh` JSON wire shape maps **to/from** the normalized structs in
[adapter-interface.md](adapter-interface.md) (`issue` / `comment` /
`status {raw, normalized}`) **at the adapter boundary**. Reconcile (fn-52.4/.5)
only ever sees the normalized form — a transport bug stays in this file; a merge
bug stays in reconcile.

| normalized `issue` field | GitHub source (`gh issue view --json …`) | Notes |
|---|---|---|
| `id` | `id` (node id `I_kwDO…`) | **durable dedupe key** — stored via `sync set-tracker-id`. Never the `number`. |
| `identifier` | `"#" + number` (e.g. `#123`) | display only; surfaced in listings. |
| `title` | `title` | |
| `body` | `body` | free-form markdown. |
| `status.raw` | `state` + `stateReason` (+ `status:` label) | the literal GitHub signal. |
| `status.normalized` | the read-mapping table above | reduced-fidelity recovery via `status:` label. |
| `priority` | (none native) — a `priority:*` label if the repo uses one | folded, never auto-changed (R7). |
| `labels` | `labels[].name` | includes the `flow:<id>` back-reference label AND the `status:*` label. |
| `url` | `url` | |
| `updatedAt` | `updatedAt` | drives staleness + echo-suppression. |

`tracker`/`type` on the struct are set to `"github"` / `"issue"`.

## The six interface methods over `gh`

Mapping wire ↔ normalized happens here, at the adapter boundary. Reconcile never
sees a `gh` JSON shape. (`-R <repo>` is the configured `tracker.perTracker.repo`;
omit it when running inside the target repo's checkout.)

### `fetchIssue(trackerId)` → normalized `issue` | not-found

```bash
gh issue view "$NUMBER" -R "$REPO" \
  --json id,number,title,body,state,stateReason,labels,url,updatedAt,author
```
- Map per the table above. `state`/`stateReason`/`status:` label → `status`.
- **not-found:** a deleted/transferred/404 issue makes `gh issue view` **exit
  non-zero** with `Could not resolve to an Issue` (or `404`) on stderr ⇒ return
  `not-found` — **never raise out of the adapter**. The skeleton then emits an
  `errored` receipt + prompts/queues unlink (see the error contract below).

### `writeIssue(issue)` → `{id, identifier, url}` (upsert)

```bash
# CREATE (no issue.id) — body via --body-file - to dodge shell quoting.
# `gh issue create` has NO --json output; it prints the new issue's URL on stdout.
URL=$(printf '%s' "$BODY" | gh issue create -R "$REPO" \
        --title "$TITLE" --body-file - \
        --label "flow:$FLOW_ID" --label "status:$NORMALIZED_STATUS")
NUMBER=$(printf '%s' "$URL" | sed -E 's@.*/issues/([0-9]+).*@\1@')
# Re-view to capture the durable node id (the create output has no id):
gh issue view "$NUMBER" -R "$REPO" --json id,number,url

# UPDATE (issue.id present) — number is the positional arg:
printf '%s' "$BODY" | gh issue edit "$NUMBER" -R "$REPO" \
  --title "$TITLE" --body-file -
```
- **Upsert by presence of `issue.id`** (interface rule): no id ⇒ create; id ⇒ edit.
- `gh issue create` prints only the URL (no `--json`), so after a **create**
  derive the `number` from the URL and re-view once
  (`gh issue view --json id,number,url`) to capture the **node id**; return
  `{ id (node id), identifier ("#"+number), url }`.
- Write the flow back-reference on create/first-link: a `flow:<id>` label (and the
  initial `status:<normalized>` label) so the issue points back at the spec.
- `gh issue create` does **not** support label-create-on-the-fly — pre-create the
  `flow:*` / `status:*` labels at config time, or `gh label create` on demand.

### `setStatus(trackerId, status)` → ok | errored

Apply the write-mapping table above:

```bash
case "$NORMALIZED" in
  done|verified)
    gh issue edit "$NUMBER" -R "$REPO" \
      --add-label "status:$NORMALIZED" $(remove_other_status_labels)
    gh issue close "$NUMBER" -R "$REPO" --reason completed ;;
  backlog|planned|in-progress|in-review)
    gh issue reopen "$NUMBER" -R "$REPO" 2>/dev/null   # no-op if already open
    gh issue edit "$NUMBER" -R "$REPO" \
      --add-label "status:$NORMALIZED" $(remove_other_status_labels) ;;
  deferred|wontfix)
    : ;;   # R7: surface to the user / queue — NEVER auto-close as "not planned"
esac
```
- A `gh` non-zero exit (bad number, perms, label-not-found) ⇒ return `errored`
  (don't crash). The skeleton writes an `errored` receipt and does not advance
  state.
- `remove_other_status_labels` ⇒ `--remove-label` for each `status:*` not being
  set (keeps the namespace single-valued).

### `listComments(trackerId)` → normalized `comment[]`

```bash
gh issue view "$NUMBER" -R "$REPO" \
  --json comments -q '.comments[] | {id, author: .author.login, body, createdAt, url}'
```
- **GitHub comment ids are stable** (the node id `IC_kwDO…` on each comment) —
  same dedup property the Linear comments rely on; safe as the dedup key.
- Map each: `author.login`→`author`; `body`, `createdAt`; **detect the
  `flow-evt:<event>` marker** in `body` → set `marker` (flow's own echo, skipped
  on pull); genuine tracker-side comments get `marker:null` and pull into the spec
  sync log. Same dedup-marker scheme as fn-52.5 ([comments-sync.md](comments-sync.md)).
- `gh issue view --json comments` returns all comments inline (no manual paging
  needed for typical issues); for very large threads page via
  `gh api repos/{owner}/{repo}/issues/{number}/comments --paginate`.

### `postComment(trackerId, body)` → normalized `comment`

```bash
printf '%s' "$BODY_WITH_MARKER" | gh issue comment "$NUMBER" -R "$REPO" --body-file -
```
- `$BODY_WITH_MARKER` carries the `flow-evt:<event>` marker line (echo suppression
  + dedup, per [comments-sync.md](comments-sync.md)).
- `gh issue comment` prints the new comment's URL; re-`listComments` (or
  `gh api …/comments` with the URL) to recover the node id for the returned
  normalized `comment`.
- **`--body-file -`**, never raw `--body` (markdown quoting).

### `readStatus(trackerId)` → normalized `status`

Derived from the `fetchIssue` `state` + `stateReason` + `status:` label — no
separate call (same as Linear deriving status from `state{name type}`).

## `makePr` — link the PR to the issue (native GitHub, no "Diffs")

When the tracker is **GitHub**, the spec maps to a GitHub *issue* and the PR lives
in the same repo, so linkage is **native GitHub cross-referencing** — no Linear
attachment, no Linear Diffs (GitHub has its own PR review UI). make-pr §4.6a's
Linear branch is GitHub-typed-skipped; instead the GitHub adapter ensures the PR
body carries a **non-closing** reference to the issue — `Refs #<number>` (NOT
`Fixes #<number>`, which would auto-close the issue on merge and bypass
spec-completion-review; flow-next owns the lifecycle, R7/R10). GitHub then renders
the PR↔issue cross-link automatically. Gate is the same as Linear: bridge **active
AND tracker.type == github** — no separate `makePr` opt-in. There is no rich-attach
step (the cross-reference IS the link).

## Capability parity (GitHub ↔ Linear) — the R13 guarantee

Reconcile is genuinely transport-blind only if the GitHub adapter produces the
**same normalized structs** the Linear adapter does, for every interface method.
Verify per method:

| Interface method | GitHub (`gh`) | Linear ([linear-ladder.md](linear-ladder.md)) | Parity target |
|---|---|---|---|
| `fetchIssue` | `gh issue view --json …` | `get_issue` / `issue(id)` | same `issue` struct (title/body/status/priority/labels/url/updatedAt) |
| `writeIssue` (upsert) | `gh issue create` / `gh issue edit` | `save_issue` / `issueCreate`/`issueUpdate` | same `{id, identifier, url}` |
| `listComments` | `gh issue view --json comments` | `list_comments` / `comments(first:N)` | same `comment[]` (author/body/createdAt/marker) |
| `postComment` | `gh issue comment --body-file -` | `save_comment` / `commentCreate` | same `comment` |
| `readStatus` | from `state`+`stateReason`+`status:` label | from `state{name type}` | same `status{raw,normalized}` |
| `setStatus` | `gh issue close/reopen` + `status:` label | `save_issue(state)` / `issueUpdate(stateId)` | ok / `errored` |
| status map | open/closed+reason+`status:` label (reduced — recovered via label) | team `workflowStates` / `list_issue_statuses` | same **normalized** vocabulary out |

The fidelity gap (GitHub's two-value native state) is bridged by the `status:`
label so the **normalized output is identical** — that is what makes reconcile
transport-blind despite GitHub's poorer native model. If a `status:` label is
absent (human-edited issue), the read-mapping table degrades gracefully to a
best-effort normalized value; that is a documented reduced-fidelity case, not a
parity break (the struct shape is still identical).

## Transport-blind proof / round-trip spike (acceptance #3 — run FIRST)

The R13 guarantee: **the same reconcile path over `gh` fixtures yields merge
output identical to the Linear path.** Two checks:

### A. Round-trip spike (transport in isolation — no merge)

Push a flow body to a real GitHub issue, then pull it back — format translation
only. Surfaces transport bugs (auth, `--body-file` escaping, number-vs-node-id,
markdown round-trip) BEFORE relying on reconcile.

> **Live-verification status (this environment).** A live GitHub round-trip needs
> a real `GH_TOKEN` against a real repo with issue write access — unavailable in
> the build environment, so the **live execution is deferred to the post-PR
> smoke-testing phase** the maintainer drives. The spike below is a complete,
> runnable procedure with an explicit success/fail oracle; the `gh` flags + JSON
> fields it depends on are verified and pinned above (gh ≥ 2.x). Run it once.

Fixture (the same canonical flow body the Linear spike uses — headings, a
checklist, a fenced block, a link — the structures most likely to be mangled):

~~~markdown
## Goal
Round-trip fixture for the GitHub transport spike.

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
2. **Push (create)** via `writeIssue` (no id ⇒ create), body via `--body-file -`:
   ```bash
   NUM=$(gh issue create -R "$REPO" --title "flow spike" \
           --body-file /tmp/spike-flow-body.md \
           | sed -E 's@.*/issues/([0-9]+).*@\1@')
   ```
3. **Pull back** via `fetchIssue(number)`:
   ```bash
   gh issue view "$NUM" -R "$REPO" --json body -q .body > /tmp/spike-pulled-body.md
   ```
4. **Oracle (success/fail):**
   ```bash
   if diff -u /tmp/spike-flow-body.md /tmp/spike-pulled-body.md; then
     echo "SPIKE PASS — round-trip preserved the body"
   else
     echo "SPIKE FAIL — gh transport mangled the body; see diff above"
   fi
   ```
   A non-empty diff is a transport bug to fix here BEFORE relying on reconcile —
   e.g. GitHub normalizing trailing whitespace or line endings. (If GitHub
   canonicalizes markdown in a stable, loss-less way, record that exact canonical
   form as the fixture's expected output so .4 reconciles against *that*.)
5. **Cleanup:** `gh issue close "$NUM" -R "$REPO" --reason "not planned"` (or
   delete via `gh issue delete "$NUM" -R "$REPO" --yes` where the token allows).

The spike writes a receipt like any sync run:
`sync receipt <spec> --status noop --transport gh --note "round-trip spike: PASS|FAIL"`
(status `noop` — a transport probe, not a sync of a tracked spec; no `--event`
either — the spike is a manual diagnostic, never a lifecycle touchpoint).

### B. Cross-tracker reconcile parity (the actual R13 check)

Feed the **same normalized fixtures** through reconcile twice — once with the
GitHub adapter's output structs, once with the Linear adapter's — and assert the
merge output is identical:

```bash
# Pseudo-procedure (reconcile is agentic — fn-52.4/.5 — and consumes structs):
#   1. Take a flow body + a base snapshot + a tracker-side edit.
#   2. Produce the normalized `issue`/`comment`/`status` structs TWICE:
#        - via the GitHub mapping tables above (open/closed+reason+status: label)
#        - via the Linear mapping (state{name type})
#      Construct both so they represent the SAME logical state (e.g. GitHub
#      OPEN+`status:in-progress` ≡ Linear `started`/`in-progress`).
#   3. Run the UNCHANGED reconcile core (body-merge.md / status-sync.md /
#      comments-sync.md) on each struct set against the same base.
#   4. Oracle: the two merge outputs are identical (same merged body, same
#      who-wins status, same comment dedup). Any difference is a mapping bug in
#      an adapter — NOT a reconcile change. Reconcile is never edited to make a
#      transport pass.
```

This is the load-bearing R13 assertion: identical reconcile output across Linear
and GitHub fixtures, with the reconcile core touched in neither task.

## Error contract (acceptance #4) — never crash, never corrupt state

The adapter honors the [adapter-interface.md](adapter-interface.md) contract rules.
The failure modes that MUST be non-destructive:

- **Missing / deleted / transferred / 404 linked issue** — `gh issue view` exits
  non-zero (`Could not resolve to an Issue`, `404`). `fetchIssue` returns
  `not-found` (NEVER raises). The skeleton then:
  - emits `sync receipt … --status errored --transport gh ${EVENT:+--event "$EVENT"}`,
  - does **NOT** crash, does **NOT** clear state, does **NOT** advance
    `lastSyncedAt` (a failed fetch must never corrupt the merge base),
  - prompts the user to unlink (interactive) or queues an unlink decision
    (`sync defer`, Ralph) — never a silent `sync clear`.
- **Unauthenticated mid-run** (`GH_TOKEN` expired/revoked) — `gh` exits with an
  auth error. Treat as the **no-op rung** for that operation: `noop` receipt
  + note, no state write — same as never having had a transport.
- **Rate limit** — GitHub returns **HTTP 403/429 with `Retry-After` /
  `X-RateLimit-Reset`** (NOT Linear's complexity 400). `gh` surfaces a non-zero
  exit + stderr message. **Back off and retry** (exponential, honor the reset
  hint) rather than failing the run.
- **Batch sync is item-level** — one spec's `errored`/rate-limit does not abort
  the batch: that spec gets its own `errored` receipt + no state write, and the
  run continues to the next spec.
- **Echo suppression** — after a push, the resulting tracker-side body hash is
  recorded (rides on the merge-base snapshot, fn-52.4); the next pull's matching
  hash ⇒ flow's own echo ⇒ `noop`, never a phantom conflict. `updatedAt` from the
  `gh` JSON helps distinguish a real GitHub-side edit from an echo. Comment echo
  uses the `flow-evt:<event>` marker (above), same as Linear.

## Boundaries

- **This is the transport, not the merge.** The adapter maps `gh` JSON ↔
  normalized and routes the single rung / no-op. The 3-way body merge
  ([body-merge.md](body-merge.md), fn-52.4), the status who-wins
  ([status-sync.md](status-sync.md), fn-52.5), and the comments/evidence append +
  dedup ([comments-sync.md](comments-sync.md), fn-52.5) consume the normalized
  structs and live in those tasks — **reused unchanged** here.
- **Reduced fidelity is by design.** GitHub's two-value native state cannot match
  Linear's workflow taxonomy; the `status:` label bridges it so the *normalized*
  output is identical. Document the gap (above); do not invent a richer GitHub
  state model.
- **No new hard dependency.** `gh` is not required; the terminal rung is a
  documented no-op. The zero-dep base install is untouched (spec Boundaries /
  STRATEGY opt-in carve-out).
- **One GitHub repo per linked spec** (`tracker.perTracker.repo`) — the bridge
  config resolves a single `owner/repo` per repo, mirroring the one-team Linear
  constraint.
- **Codex mirror** (sync-codex.sh) is regenerated in fn-52.9 — keep this file
  Claude-native; no Codex-specific edits here.
