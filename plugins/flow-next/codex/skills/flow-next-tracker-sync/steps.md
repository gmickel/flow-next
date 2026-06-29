# flow-next-tracker-sync — phase-by-phase execution

Read [SKILL.md](SKILL.md) first for the architecture, the flowctl-vs-skill split, and the boundaries. This file is the execution detail. `$FLOWCTL` is defined in SKILL.md's Preamble.

This file is the transport-blind orchestration **spine**: discovery ceremony, link/unlink ceremony, grain, identity, and the push/pull/reconcile skeleton with named hooks. The hook bodies live in dedicated reference files: transports (`fetchIssue`/`writeIssue`/… — Linear [`references/linear-ladder.md`](references/linear-ladder.md), GitHub [`references/github.md`](references/github.md), GitLab [`references/gitlab.md`](references/gitlab.md), Jira [`references/jira.md`](references/jira.md)) and reconcile (3-way body merge [`references/body-merge.md`](references/body-merge.md); status who-wins [`references/status-sync.md`](references/status-sync.md); comments/evidence append [`references/comments-sync.md`](references/comments-sync.md)), all plugging through the contract in [`references/adapter-interface.md`](references/adapter-interface.md). Inline, a hook points at its reference with **[→ ref: <file>]** — read that file for the body; this file owns only the routing.

## Phase 0 — Mode + Ralph/autonomous awareness

Parse `$ARGUMENTS` for an optional operation token (`push` / `pull` / `reconcile` / `comment` / `list-open` / `list-relations` / `question` / `link` / `unlink` / `discover`) and an optional spec id (or, for `question` / `list-relations`, a `<spec-id | tracker-id>`). With none, default to the interactive menu (discover if the bridge is inactive, else offer push/pull/reconcile over `list-unsynced` / `list-stale`).

`comment <spec-id>` is the lifecycle-event op the host skills invoke for opted-in touchpoints (`work.done` / `resolvePr` / `completionReview` / `qa` set to `comment` — see SKILL.md's perEvent table). It routes to the **comments-sync hook** (`postLifecycleComment` → `postComment` **[→ ref: comments-sync.md]**): append the structured lifecycle comment + evidence, dedup, receipt — it does NOT touch the body or status. Like `push` / `reconcile`, a `comment` op on an unlinked spec triggers the **Phase 3 create-if-unlinked** flow-first link first (create + attach), then posts the comment on the now-linked spec.

`list-open`, `list-relations <tracker-id>`, and `question <spec-id | tracker-id>` are the **backlog-mode named ops** (fn-68 — pilot's autonomous floor scheduler invokes them). Here `<tracker-id>` is the issue's **tracker handle** — the display `identifier`, not the opaque global id. For a **tracker-only** subject (no flow spec) the value passed is the `listOpenIssues` normalized `issue.identifier` (`<project>#<iid>` / `WOR-17` / `#123`): on GitLab the adapter must index `/projects/:id/issues/:iid` from the `<project>#<iid>` it carries (a global id is not a valid path index; gitlab.md § identity). The op drives the adapter with this identifier **directly** — it does **not** rely on `flowctl` resolving a bare GitLab key (the resolver accepts only `fn-*` / `KEY-N`; a `<project>#<iid>` does not resolve). A spec-backed subject passes its `<spec-id>`, which resolves to the stored `tracker.identifier`. They are **skill-level, transport-blind operations** — NOT new flowctl transport (flowctl has no tracker transport and must not grow one). `list-open` enumerates the promoted-lane open issues via the `listOpenIssues` adapter method; `list-relations` READS one issue's dependency relations via the `listIssueRelations` adapter method (dep-ordering edges, never a write); `question` posts a question-valve comment carrying the stable anchor. All route through the same adapter ladder as every other op. See **Phase 7 — Backlog-mode ops** below for their bodies.

**Event tag (fn-57 / R1).** When a lifecycle touchpoint invokes this skill, the invocation carries the perEvent key it serves — an `event: <perEvent-key>` token alongside the operation, e.g. `skill: flow-next-tracker-sync (operation: comment <spec-id>, event: work.done)`. Parse it into `EVENT`; **every `sync receipt` this run** then carries `--event "$EVENT"` — the call sites here and in the reference files use `${EVENT:+--event "$EVENT"}`, which expands to nothing when `EVENT` is empty, so one call-site shape serves both modes. The tag is what `flowctl sync check` audits at end-of-skill (an untagged receipt never clears a lifecycle event). **Manual invocations are NOT lifecycle touchpoints** — a user typing `/flow-next:tracker-sync push <id>`, the interactive menu, the discovery ceremony, `unlink`, and the round-trip spikes all leave `EVENT` empty, and their receipts legitimately carry no event tag (null event = not a lifecycle touchpoint).

**Ralph / autonomous mode** (R11 + fn-68 R14): when `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH` is set, **`FLOW_AUTONOMOUS=1`, or the `mode:autonomous` token is present in `$ARGUMENTS`** (strip it — same parse shape as work / make-pr / resolve-pr / capture), the skill still runs — but the discovery ceremony NEVER prompts (it needs a human; if the bridge isn't already configured, no-op + receipt note), and any genuine conflict / id collision / readyState-label failure **queues** (`sync defer`) instead of asking. Confident merges and conflict-free status/comment ops proceed unattended. "Ask the human" resolves to "queue for the human" in autonomous mode — same policy, surface-dependent delivery (mirrors fn-51's surface-aware ladder). Every per-tick tracker interaction on the pilot/backlog path is therefore fully unattended — **`plain-text numbered prompt` is never reachable under the marker** (fn-68 R14: backlog mode's lifecycle sync could otherwise reach a prompt and hang).

The autonomy marker family folds into the **single `RALPH` gate** below — tracker-sync's "never prompt, queue instead" policy is identical for all four signals, so they collapse to one flag (unlike work / make-pr, which keep `RALPH` and `AUTONOMOUS` separate because they differ on receipt obligations; tracker-sync has none of that split — it queues conflicts the same way regardless of which signal fired). This makes tracker-sync match the autonomy-parity of every other lifecycle-participating skill; it was the **one** whose gate omitted `FLOW_AUTONOMOUS`.

```bash
RALPH=0
# fn-68 R14: recognize the FULL autonomy marker family (FLOW_AUTONOMOUS / mode:autonomous),
# not just FLOW_RALPH / REVIEW_RECEIPT_PATH — parity with work / make-pr / resolve-pr / capture.
[[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
 || "${FLOW_AUTONOMOUS:-}" == "1" || "$ARGUMENTS" == *mode:autonomous* ]] && RALPH=1
# Lifecycle event tag (fn-57): the caller's `event:` token, e.g. work.firstClaim |
# work.done | work.completionReview | capture | makePr | resolvePr. Empty on manual runs.
EVENT="<perEvent-key from the invocation, or empty>"
```

> **Autonomy parity is a hard invariant (fn-68 R14).** Under `RALPH=1` NO code path may reach `plain-text numbered prompt` — the discovery ceremony (Phase 1), the collision guard (Phase 2c / Phase 3), the genuine-conflict surface (Phase 4), and the `question`-op authoring (Phase 7) ALL resolve their "ask the human" to `sync defer` (queue) when `RALPH=1`. A backlog-mode tick that hit a live prompt would stall the whole autonomous loop, so this gate is what makes tracker-sync safe to call per-tick from pilot.

## Phase 1 — Discovery ceremony (R2)

Only when the bridge is not yet active (`flowctl sync active --json` → `active: false`) AND not in Ralph mode. If already active, skip to Phase 2.

1. **Probe the six signals** (see SKILL.md table). Detection lives here, not flowctl:
 ```bash
 # Linear MCP: inspect the host's MCP/tool list for a Linear server (verified upsert
 # verbs save_issue / save_comment / list_comments / get_issue / list_issue_statuses —
 # see references/linear-mcp.md). Host-agent introspection — no flowctl call.
 LINEAR_API=0; [ -n "${LINEAR_API_KEY:-}" ] && LINEAR_API=1
 GH_OK=0; gh auth status >/dev/null 2>&1 && GH_OK=1
 # GitLab: a logged-in `glab` session OR a GITLAB_TOKEN / CI_JOB_TOKEN env token
 # (the headless REST fallback). Either ⇒ GitLab transport available
 # (references/gitlab.md). Self-managed hosts are honored via glab's configured
 # host / CI_SERVER_URL — never assume gitlab.com.
 GLAB_OK=0; glab auth status >/dev/null 2>&1 && GLAB_OK=1
 [ -n "${GITLAB_TOKEN:-}${CI_JOB_TOKEN:-}" ] && GLAB_OK=1
 # Jira: the REST signal — JIRA_BASE_URL plus a credential. Cloud needs
 # JIRA_EMAIL + JIRA_API_TOKEN (HTTP-basic email:API_TOKEN); self-hosted
 # Data Center / Server needs JIRA_PAT (Authorization: Bearer <PAT>). Either
 # credential alongside JIRA_BASE_URL ⇒ Jira REST transport available — flow-next
 # offers it (references/jira.md). NO MCP probe: Jira is REST-only (the official
 # Atlassian MCP can't transition status / update fields / set links — the writes
 # a two-way sync needs — and the community MCP is a redundant PAT-wrapper; the
 # fn-70 transport decision). A bare `*.atlassian.net` host with no credential is
 # still SURFACED (so the user knows why Jira can't be offered), but only a
 # JIRA_BASE_URL + credential pair OFFERS it.
 # Offer Jira only when the credential MATCHES the deployment the baseUrl implies:
 # Cloud (*.atlassian.net) ⇒ email + API token (cloud-basic); self-hosted DC/Server ⇒
 # Bearer PAT. A Cloud URL with only a PAT (or a self-hosted URL with only Cloud
 # email/token) is a MISMATCH → surfaced, NOT offered (the persisted authScheme would
 # otherwise be wrong and every call 401).
 JIRA_OK=0
 if [ -n "${JIRA_BASE_URL:-}" ]; then
 JBL_LC=$(printf '%s' "$JIRA_BASE_URL" | tr '[:upper:]' '[:lower:]') # host match is case-INSENSITIVE (Atlassian.net == atlassian.net)
 case "$JBL_LC" in
 *.atlassian.net*) [ -n "${JIRA_EMAIL:-}" ] && [ -n "${JIRA_API_TOKEN:-}" ] && JIRA_OK=1 ;; # canonical Cloud → cloud-basic
 *) # CUSTOM DOMAIN — Cloud OR self-hosted (a Cloud tenant on an Atlassian custom domain
 # does NOT end in .atlassian.net). Offer if EITHER credential scheme is present; the
 # authScheme detection below disambiguates (email+token ⇒ cloud-basic; PAT ⇒ bearer-pat; both ⇒ ASK).
 { { [ -n "${JIRA_EMAIL:-}" ] && [ -n "${JIRA_API_TOKEN:-}" ]; } || [ -n "${JIRA_PAT:-}" ]; } && JIRA_OK=1 ;;
 esac
 fi
 ```
 The Linear transport rung the bridge will use follows from these signals (MCP
 beats GraphQL when both present): MCP registered → rung 1; else `LINEAR_API_KEY`
 set → rung 2 (GraphQL); else no-op. See [`references/linear-ladder.md`](references/linear-ladder.md).
2. **Surface present AND absent.** Tell the user what was found and what wasn't — e.g. "Linear MCP: present. LINEAR_API_KEY: absent. gh: authenticated. glab: authenticated. Jira: JIRA_BASE_URL + JIRA_API_TOKEN present (Cloud)." Absent signals matter (they explain why a transport is unavailable) — e.g. "Jira: JIRA_BASE_URL present but no JIRA_EMAIL+JIRA_API_TOKEN / JIRA_PAT → surfaced, can't offer until a credential is set."
**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

3. **ASK via `plain-text numbered prompt`**. Lead with the recommended tracker (the strongest present signal) + a one-sentence rationale. Ask: enable the bridge? which tracker (`linear` / `github` / `gitlab` / `jira`)? **Enabling activates the WHOLE pipeline by default (opt-out model)** — tell the user that on confirmation every lifecycle event (capture / interview / plan / work.firstClaim / work.done / makePr / resolvePr / completionReview) starts mirroring to the tracker, because hooking up the bridge means you want it to sync. Offer an **optional opt-out**: any events to exclude now (default: all on); they can also turn any off later via `flowctl config set tracker.perEvent.<event> off`. Resolution is **env > config > ASK** — don't re-ask anything env/config already decided.
4. **On confirmation, write config** (dot-paths are safe). Activate every lifecycle event to its natural op — **skip only the ones the user explicitly excluded in step 3**:
 ```bash
 $FLOWCTL config set tracker.enabled true
 $FLOWCTL config set tracker.type "$CHOSEN_TYPE" # linear | github | gitlab | jira
 $FLOWCTL config set tracker.provenance "discovery ceremony $(date -u +%Y-%m-%d); confirmed by <who>; signals: <list>"
 # DEFAULT-ON (opt-out): activate the whole pipeline so it mirrors end-to-end.
 $FLOWCTL config set tracker.perEvent.capture reconcile # two-way body sync on capture
 $FLOWCTL config set tracker.perEvent.interview reconcile # two-way body sync on interview
 $FLOWCTL config set tracker.perEvent.plan reconcile # project the planned spec
 $FLOWCTL config set tracker.perEvent.work.firstClaim push # move the issue In-Progress
 $FLOWCTL config set tracker.perEvent.work.done comment # status comment + evidence
 $FLOWCTL config set tracker.perEvent.makePr comment # PR link is unconditional; extra status comment
 $FLOWCTL config set tracker.perEvent.resolvePr comment # resolution comment
 $FLOWCTL config set tracker.perEvent.completionReview comment # fn-66: verdict + R-ID coverage comment; NEVER terminal Done (land.merged is the sole Done driver)
 $FLOWCTL config set tracker.perTracker.teamId "<team>" # Linear: if the user named one
 # GitLab (tracker.type gitlab) — parallel to GitHub's `repo`: write the
 # group/project path (nested groups allowed, e.g. `group/subgroup/repo`) and,
 # only for self-managed, the BARE HOSTNAME (no scheme). Omit `host` on gitlab.com —
 # the adapter's host resolution defaults to `gitlab.com`, so even a token-only REST
 # sync (no glab, no CI_SERVER_URL) still builds https://gitlab.com/api/v4. Skip both
 # for linear/github.
 $FLOWCTL config set tracker.perTracker.project "<group/project>" # GitLab: the group/project path
 $FLOWCTL config set tracker.perTracker.host "<gitlab.example.com>" # GitLab self-managed: a BARE HOSTNAME (no scheme) — `glab api --hostname` needs a host, not a URL; the REST rung derives https://<host>/api/v4. Omit on gitlab.com.
 # Jira (tracker.type jira) — write the site + project key, and PERSIST the
 # deployment shape the probe detected so runtime never re-infers. The auth
 # scheme + api version are DETECTED at the ceremony: a *.atlassian.net baseUrl ⇒
 # cloud-basic + apiVersion 3. A CUSTOM DOMAIN (Cloud tenant not on .atlassian.net,
 # OR self-hosted) can't be told apart by URL → infer from the CREDENTIAL: only
 # email+token ⇒ cloud-basic + v3; only PAT ⇒ bearer-pat + v2.
 # (a *.atlassian.net baseUrl ⇒ cloud-basic + apiVersion 3; else infer from the
 # credential as above; if BOTH JIRA_API_TOKEN and JIRA_PAT are present AND the
 # deployment is genuinely ambiguous, ASK — never silently guess — then persist).
 # Credentials stay in env (read each run), never written here. Skip all for
 # linear/github/gitlab.
 $FLOWCTL config set tracker.perTracker.baseUrl "<https://acme.atlassian.net>" # Jira: the site base (JIRA_BASE_URL env overrides; the persisted value is the default — never inert)
 $FLOWCTL config set tracker.perTracker.projectKey "<PROJ>" # Jira: the project key (the JQL / listOpenIssues scope)
 $FLOWCTL config set tracker.perTracker.authScheme "<cloud-basic|bearer-pat>" # Jira: cloud-basic (Cloud HTTP-basic email:API_TOKEN) | bearer-pat (DC/Server Bearer PAT) — detected, persisted; runtime reads only this
 $FLOWCTL config set tracker.perTracker.apiVersion "<3|2>" # Jira: 3 (Cloud /rest/api/3, ADF) | 2 (DC/Server /rest/api/2) — the REST endpoint family the adapter branches on
 # statusMap — WRITE IT NOW or Jira status sync is inert: setStatus DEFERS every status
 # with no statusMap entry (references/jira.md § Status / transitions), so an unset map
 # means an active bridge that never projects status. AUTO-DERIVE it from the project's
 # workflow when the credential is present, then surface for the user to refine:
 # GET /rest/api/$APIV/project/$PROJ/statuses → issue-type → [{id,name,statusCategory:{key}}].
 # Map the FULL normalized set by name first, then statusCategory.key:
 # done / verified → a status with statusCategory.key=="done"
 # in-progress → "In Progress" (category indeterminate)
 # in-review → "In Review" / "Review" IF present (else leave UNMAPPED → setStatus
 # defers for in-review only; never invent a transition the workflow lacks)
 # planned → "To Do" / "Backlog" (category new)
 # Write id-keyed (ids are rename-stable): {"in-progress":{"id":"3"},"done":{"id":"10001"},…}.
 $FLOWCTL config set tracker.perTracker.statusMap "$DERIVED_STATUSMAP_JSON" # Jira: normalized→{id|name}; auto-derived (refine later via config). NO creds at ceremony ⇒ write {} AND tell the user status sync defers until they set it (never silently inert).
 $FLOWCTL sync active --json # confirm active: true
 ```
 **Never assume — but default-on is not assuming.** No signal / user declines the bridge ⇒ write nothing; `enabled` stays `false`; `sync active` stays `active: false`. Confirming the bridge IS the consent to sync the pipeline. The **config schema default stays `off`** (in `get_default_config()`), so a bare `tracker.enabled=true` set by hand or a script — WITHOUT this ceremony — activates **no lifecycle-event sync** (every `perEvent` event stays dormant). The **two exceptions** are unconditional whenever the bridge is active (no per-event gate, by design): (1) make-pr's PR↔issue link **and its In Review status push** (fn-66, R2 — an open PR is the In Review rung, riding the same Diffs-powering link path); (2) **`land.merged`** (fn-66, R10 — a real merge is the SOLE event that projects terminal `Done`, gated on the GitHub `MERGED` probe; leaving it opt-in would strand boards at In Review post-merge). Only the ceremony's explicit per-event writes activate the other events themselves. Users opt out per event afterward via `flowctl config set tracker.perEvent.<event> off`.
5. **Readiness state (fn-58, R4 — optional, skippable).** After the config writes, ask one more question via `plain-text numbered prompt`: *which tracker workflow state means "ready for work"?* When set, every pull-side sync projects that state onto the local spec `ready` flag ([→ ref: status-sync.md] § Readiness projection) — **the tracker becomes authoritative for readiness** (a local `flowctl spec ready` is overwritten on the next sync). Readiness is optional: always offer **skip** (and lead with it when no candidate state exists); skipping writes nothing and leaves `tracker.readyState: null` — the readiness gate stays dormant (R7).
 - **Linear** — discover the team's states first: MCP `list_issue_statuses(team:<team>)` → `{id, name, type}` per state (GraphQL rung: `workflowStates(first:100, filter:{team:{name:{eq:$team}}}){ nodes { id name type } }` — explicit `first:` on every connection). Lead with a recommendation: a state whose **name** looks like "Ready" / "Next" / "Ready for Dev" (case-insensitive); if none, lead with skip. Validate the chosen state resolves (`get_issue_status(<id or name>)`) before writing. Store the state **name** (names are what humans see; the projection matches case-insensitive/trimmed).
 - **GitHub** — issues have no workflow states; readiness resolves to a **label** name (suggest `ready`). Pre-create it so the projection never trips on a missing label — tolerate **only** already-exists (the create fails with a 422 when the label exists; that is fine, idempotent). Any other failure (auth / permissions / wrong repo / API) must surface — never write `tracker.readyState` for a label that isn't confirmed to exist, or every later pull hits the stale-config warn/noop (github.md § Readiness label) and the flag never moves:
 ```bash
 LABEL_OK=1
 if ! CREATE_ERR=$(gh label create "$READY_LABEL" -R "$REPO" \
 --description "flow-next: spec ready for execution" \
 --color 0E8A16 2>&1); then
 LABEL_OK=0 # nonzero exit — tolerate ONLY already-exists: confirm the label is really there
 gh label list -R "$REPO" --search "$READY_LABEL" --json name --jq '.[].name' \
 | grep -qix -- "$READY_LABEL" && LABEL_OK=1 # exists ⇒ 422 was idempotent, proceed
 fi
 [ "$LABEL_OK" = 1 ] && $FLOWCTL config set tracker.readyState "$READY_LABEL" # Linear: the state name instead
 ```
 If `LABEL_OK` stays 0 the label does NOT exist and the create genuinely failed: show the user `$CREATE_ERR` and re-ask via `plain-text numbered prompt` — retry, pick a different label, or skip (skip ⇒ `tracker.readyState` stays null, gate dormant per R7). Don't reach for `gh label create --force` — it silently overwrites an existing label's color/description, which is not our intent.
 - **GitLab** — like GitHub, GitLab issues have no rich workflow; readiness resolves to a **label** name (suggest `ready`). Same pre-create-and-confirm discipline as GitHub (mirrors github.md / the block above): pre-create the label via the adapter so the projection never trips on a missing label, **tolerate ONLY already-exists** (a label create on GitLab returns a 409/`already exists` when present — that is idempotent and fine), and **never write `tracker.readyState` for a label that isn't confirmed to exist**, or every later pull hits the stale-config warn/noop (gitlab.md § Readiness label) and the flag never moves. The create call itself (`glab api` / REST `POST /projects/:id/labels`) is documented in [`references/gitlab.md`](references/gitlab.md); the ceremony invokes it through the adapter (`$PROJECT` = `tracker.perTracker.project`, host-resolved):
 ```bash
 LABEL_OK=1
 # POST /projects/:id/labels — :id is the URL-encoded `group/project` path.
 # 201 ⇒ created; a 409 / "already exists" is the idempotent no-op we tolerate.
 # ${HOST:+--hostname "$HOST"} pins the configured self-managed host (tracker.perTracker.host);
 # without it glab api targets the current git dir's host / gitlab.com → could create `ready`
 # on the WRONG instance and then persist tracker.readyState, so later syncs warn/noop.
 # Use whichever rung the discovery probe resolved — glab when installed, else the
 # token-only RAW REST /api/v4 floor (Phase 1 offers GitLab on a bare GITLAB_TOKEN even
 # with glab absent, so this ceremony MUST NOT hard-require glab or it dies "command not found").
 ENC_PROJ=$(printf '%s' "$PROJECT" | jq -sRr @uri)
 if command -v glab >/dev/null 2>&1; then # glab rung (stored auth OR env token)
 CREATE_ERR=$(glab api ${HOST:+--hostname "$HOST"} --method POST "projects/$ENC_PROJ/labels" \
 -f "name=$READY_LABEL" -f "color=#0E8A16" -f "description=flow-next: spec ready for execution" 2>&1) \
 && LABEL_OK=1 || LABEL_OK=0
 else # token-only RAW REST rung (no glab installed)
 # Prefer the explicit write-scoped GITLAB_TOKEN (PAT) over the auto CI_JOB_TOKEN —
 # the job token is often allowlist-limited / read-only, so a label create would 403.
 if [ -n "${GITLAB_TOKEN:-}" ]; then GL_HDR="PRIVATE-TOKEN: $GITLAB_TOKEN"; else GL_HDR="JOB-TOKEN: ${CI_JOB_TOKEN:-}"; fi
 CREATE_ERR=$(curl -sS --fail-with-body -X POST "https://${HOST:-gitlab.com}/api/v4/projects/$ENC_PROJ/labels" \
 --header "$GL_HDR" --data-urlencode "name=$READY_LABEL" --data-urlencode "color=#0E8A16" \
 --data-urlencode "description=flow-next: spec ready for execution" 2>&1) \
 && LABEL_OK=1 || LABEL_OK=0 # --fail-with-body: nonzero on HTTP≥400 but keeps the body for the grep
 fi
 # tolerate ONLY already-exists (a 409 / "already exists" is the idempotent no-op)
 [ "$LABEL_OK" = 0 ] && printf '%s' "$CREATE_ERR" | grep -qiE 'already exists|409' && LABEL_OK=1
 [ "$LABEL_OK" = 1 ] && $FLOWCTL config set tracker.readyState "$READY_LABEL"
 ```
 If `LABEL_OK` stays 0 the create genuinely failed (auth / permissions / wrong project / API): show the user `$CREATE_ERR` and re-ask via `plain-text numbered prompt` — retry, pick a different label, or skip (skip ⇒ `tracker.readyState` stays null, gate dormant per R7). Under a write-scope-limited `CI_JOB_TOKEN` the create may be refused — surface it and skip rather than write an unconfirmed `readyState` (gitlab.md § Readiness label).
 - **Jira** — like Linear, Jira has **rich per-project workflow states** (not labels), so readiness resolves to a **Jira status NAME** used directly in the promoted-lane JQL (e.g. `"Ready for Dev"` — a raw status name, NOT a `statusMap` key; consistent with how Linear/GitHub treat `readyState`). Discover the project's statuses first and **validate the chosen name exists** before writing, so the JQL never filters on a status the project lacks (`listOpenIssues` would then return nothing and the lane stays silently empty). When a credential is present, validate via `GET /rest/api/{3|2}/project/<projectKey>/statuses` (the apiVersion from `tracker.perTracker.apiVersion`); lead with a recommendation: a status whose name looks like "Ready" / "Selected for Development" / "To Do" (case-insensitive); if none looks right, lead with skip. When **no credential is reachable** (spec-first floor), you cannot validate — allow the user to type a name on faith OR **skip → no-op backlog lane** (`tracker.readyState` stays null; `listOpenIssues` no-ops with a note, backlog mode runs flow-ready specs only). Never write `tracker.readyState` for a status you couldn't confirm exists when creds WERE available — an unconfirmed name silently empties the promoted lane:
 ```bash
 READY_OK=0
 # Read the CEREMONY-PERSISTED transport shape — auth scheme + api version were
 # decided once when the bridge was configured (above), so validation must NOT
 # re-race env. Resolution mirrors runtime: baseUrl = JIRA_BASE_URL || config
 # (env overrides the persisted default); projectKey / authScheme / apiVersion /
 # sslVerify come from config; credentials still read from env per the persisted
 # scheme. This is the SAME resolution the adapter uses at runtime (jira.md).
 JIRA_BASE=${JIRA_BASE_URL:-$($FLOWCTL config get tracker.perTracker.baseUrl --json | jq -r '.value // empty')}
 PROJ_KEY=$($FLOWCTL config get tracker.perTracker.projectKey --json | jq -r '.value // empty')
 AUTH_SCHEME=$($FLOWCTL config get tracker.perTracker.authScheme --json | jq -r '.value // empty')
 APIV=$($FLOWCTL config get tracker.perTracker.apiVersion --json | jq -r '.value // "3"')
 SSL_VERIFY=$($FLOWCTL config get tracker.perTracker.sslVerify --json | jq -r 'if .value == null then true else .value end') # `// true` would flip an explicit false (jq `//` treats false as empty)
 # Build the auth header by the PERSISTED authScheme — never by probing which
 # env var happens to be set (that is the re-race the ceremony exists to avoid).
 CRED_OK=0; JAUTH=()
 case "$AUTH_SCHEME" in
 cloud-basic) [ -n "${JIRA_EMAIL:-}" ] && [ -n "${JIRA_API_TOKEN:-}" ] && { JAUTH=(-u "$JIRA_EMAIL:$JIRA_API_TOKEN"); CRED_OK=1; } ;;
 bearer-pat) [ -n "${JIRA_PAT:-}" ] && { JAUTH=(-H "Authorization: Bearer $JIRA_PAT"); CRED_OK=1; } ;;
 esac
 # THREE distinct outcomes — never collapse them:
 # (a) no creds for the persisted scheme (CRED_OK=0) → spec-first floor:
 # cannot validate, accept on faith OR skip → no-op backlog lane.
 # (b) creds present BUT baseUrl/projectKey missing → a CONFIG ERROR, not a
 # floor: do NOT write an unvalidated readyState (an unconfirmed name
 # silently empties the lane) — surface it and re-ask / fix config / skip.
 # (c) creds + config present → VALIDATE against the project's statuses.
 READY_WRITE=0
 if [ "$CRED_OK" = 0 ]; then
 # (a) spec-first floor — no credential reachable for the persisted scheme.
 READY_OK=1; READY_WRITE=1
 elif [ -z "$JIRA_BASE" ] || [ -z "$PROJ_KEY" ]; then
 # (b) creds present but config incomplete — config error, never write.
 READY_OK=0; READY_WRITE=0
 echo "Jira readiness: credential present but baseUrl/projectKey not configured — re-run the config-write, or skip readiness." >&2
 else
 # (c) VALIDATE the chosen status NAME exists in the project. sslVerify==false
 # ⇒ -k for self-hosted internal-CA certs (opt-in, persisted; env
 # JIRA_SSL_VERIFY=false also honored).
 [ "$SSL_VERIFY" = false ] || [ "${JIRA_SSL_VERIFY:-}" = false ] && JK=(-k) || JK=()
 STATUSES=$(curl -sS "${JK[@]}" "${JAUTH[@]}" -H "Accept: application/json" \
 "$JIRA_BASE/rest/api/$APIV/project/$PROJ_KEY/statuses" 2>/dev/null \
 | jq -r '[.[].statuses[].name] | unique | .[]' 2>/dev/null)
 printf '%s\n' "$STATUSES" | grep -qix -- "$READY_STATE" && READY_OK=1
 READY_WRITE=1
 fi
 [ "$READY_OK" = 1 ] && [ "$READY_WRITE" = 1 ] && $FLOWCTL config set tracker.readyState "$READY_STATE"
 ```
 If `READY_OK` stays 0 in case **(c)** the status does NOT exist in the project: show the user the discovered status list and re-ask via `plain-text numbered prompt` — pick an existing status, or skip. In case **(b)** the credential is present but `baseUrl`/`projectKey` were never persisted (a config gap, not a spec-first floor): re-run the config-write to set them, or skip — **never** write an unvalidated `readyState`. Skipping in any case ⇒ `tracker.readyState` stays null, gate dormant per R7, `listOpenIssues` no-ops (jira.md § Readiness). The `readyState` is the **raw Jira status name** used directly in the JQL filter, escaped before interpolation (jira.md § listOpenIssues).

## Phase 2 — Link / create ceremony (R2/R3/R16)

Attach sync state **on link**. Pick the flow by where the user is starting:

### 2a — Flow-first (author-in-flow-then-push)

A `fn-NN` spec already exists. Keep the `fn-NN` id (never rename). Push body via the body-sync hook **[→ ref: body-merge.md]**, which creates the issue via `writeIssue` **[→ ref: linear-ladder.md / github.md / gitlab.md / jira.md]**, then attach state.

> **The pushed body is the COMPLETE spec — every section, in full.** The render (`renderFlowToTracker`, body-merge.md Step 3) is a *format translation*, NOT a summary: never condense, truncate, abbreviate, or drop a section. Projection means the issue mirrors the whole spec (the Step 3.5 structural gate enforces "no section silently dropped"). If you find yourself summarizing to save tokens, stop — read body-merge.md Step 3 and render the full body.

```bash
$FLOWCTL sync set-tracker-id "$SPEC_ID" "$ISSUE_UUID" --identifier "WOR-17" --url "$ISSUE_URL"
```

Write the back-reference into the issue: a `flow:<id>` label and/or a `[<id>]` title prefix (transport call — `writeIssue`/`setStatus` **[→ ref: linear-ladder.md / github.md / gitlab.md / jira.md]**) so the issue points back at the spec. The tracker key `WOR-17` becomes a resolvable alias for the `fn-NN` spec (`work wor-17` resolves — fn-52.10).

### 2b — Tracker-first (link an existing issue — "grab issue X and spec it")

Fetch the issue via the transport (`fetchIssue` **[→ ref: linear-ladder.md / github.md / gitlab.md / jira.md]**) → normalized `issue` struct. Create the spec **keyed by the tracker key** so the repo artifact mirrors the board:

```bash
$FLOWCTL spec create --tracker-first --tracker-identifier "WOR-17" --title "<issue title>" --json
# → canonical id wor-17-slug; tasks wor-17-slug.M; bare wor-17 / wor-17.M are aliases (fn-52.10).
$FLOWCTL sync set-tracker-id "wor-17-slug" "$ISSUE_UUID" --identifier "WOR-17" --url "$ISSUE_URL"
```

> **Jira grabs go TRACKER-FIRST (like Linear).** A Jira issue key `PROJ-123` IS an
> alpha-prefixed `KEY-N` (key `PROJ`, number `123`), so it takes the **same
> tracker-first path as Linear** — `spec create --tracker-first --tracker-identifier
> PROJ-123` mints a clean `proj-123-slug` canonical id (Jira keys are alnum-`-num`,
> no slugify hazard), and bare `proj-123` / `proj-123.M` resolve like `wor-17`. BOTH
> entry flows work for Jira (tracker-first AND flow-first), distinct from GitHub/GitLab
> (flow-first only — below).
>
> **Exception — a DC/Server CUSTOM key that isn't clean `KEY-N`** (underscores
> `MY_PROJECT-7`, OR a >10-char alnum key `PRODUCT2013-7`) can't mint a kebab canonical
> id, so the strict `--tracker-first` validator REJECTS it. Those grabs go **flow-first**
> like GitHub/GitLab: create an `fn-NN` spec, then `sync set-tracker-id "<fn-id>"
> "$ISSUE_ID" --identifier "MY_PROJECT-7" --url "$ISSUE_URL"` (display-only alias — stored,
> shown, back-referenced, but you never `work MY_PROJECT-7`). Standard keys (no underscore,
> ≤10-char) stay tracker-first.
>
> **GitLab grabs go FLOW-FIRST, not tracker-first.** The `--tracker-first
> --tracker-identifier` path above only accepts an **alpha-prefixed `KEY-N`** display
> key (Linear `WOR-17` / Jira `PROJ-123` → mints `wor-17-slug` / `proj-123-slug`).
> **GitHub `#N` is NOT a `KEY-N` either**
> (`#123` has no alpha key) — it too goes flow-first; only `KEY-N`-keyed
> trackers (Linear, Jira) are tracker-first. A GitLab key is `<project>#<iid>` (slashes + `#`) which
> likewise can't slugify into a canonical spec id, so `cmd_spec_create`'s strict
> validator (`validate_tracker_identifier(..., allow_reference=False)`, verified)
> rejects **both `#123` and `<project>#<iid>`** at create time (issue refs are accepted
> only at LINK time via `set-tracker-id`, `allow_reference=True`). For a GitLab grab,
> create a **flow-first `fn-NN` spec** instead, then attach the issue:
> `$FLOWCTL sync set-tracker-id "<fn-id>" "<global-issue-id>" --identifier
> "<project>#<iid>" --url "<web_url>"` — fn-69.1 widened the **`set-tracker-id`**
> validator to accept `group/subgroup/project#12` + bare `#<iid>`. The key is stored as
> the display `identifier`, but flowctl's resolver does NOT resolve a bare GitLab key
> (`fn-*` / `KEY-N` only) — use the **`fn-NN` id** for commands. (gitlab.md § identity.)

Seed the merge base from the **current issue body** so the first sync is pull-only (never surfaces the whole issue as a conflict) — first-link base-seeding is in **[→ ref: body-merge.md]**; call `sync set-merge-base` with the flow-form + tracker-form snapshots it produces:

```bash
# fn-52.4 produces both body forms; the setter requires BOTH halves together (paired-snapshot invariant):
$FLOWCTL sync set-merge-base "wor-17-slug" --flow-file flow.txt --tracker-file tracker.txt
$FLOWCTL sync set-last-synced "wor-17-slug"
```

> **Paired-snapshot invariant** (memory: `paired-snapshot-setter-must-write-both`): `sync set-merge-base` requires BOTH `--flow*` AND `--tracker*` together — never pass one half alone (it errors and leaves state unchanged). The merge base is one snapshot of both bodies at one sync point.

### 2c — Collision guard

Before linking, ensure the tracker UUID isn't already attached to another spec:

```bash
$FLOWCTL sync check-collisions --json # flags any UUID shared by >1 spec
```

If `set-tracker-id` reports a collision, ask the user (interactive) or queue (`sync defer`, Ralph) — never `--force` silently.

## Phase 3 — Orchestration skeleton (transport-blind)

**Create-if-unlinked (auto-link on first lifecycle touch).** When a lifecycle event (`capture` / `interview` / `plan` / `work.firstClaim` / `work.done` / `makePr` / `resolvePr` / `completionReview`) routes a `push` / `reconcile` / `comment` operation for a spec that has **no `tracker.id`**, run the **flow-first link first** (Phase 2 § "Author-in-flow-then-push": `renderFlowToTracker` → `writeIssue` *creates* the issue → `sync set-tracker-id` attaches the id / identifier / url + writes the back-reference → **`sync set-merge-base` (BOTH halves) + `set-last-synced`** to snapshot the just-rendered pair), **then** proceed with the requested operation on the now-linked spec. This is what makes an **active** bridge actually keep specs in sync — the 1.6.0 opt-out model ("connecting a tracker means you want it kept in sync") means a spec authored in-flow gets its issue **created on the first touchpoint that fires**, not silently left flow-local until someone manually links it. The only operation that no-ops on an unlinked spec is **`unlink`** (nothing to detach). Best-effort as ever: if no transport is reachable the create is skipped (`errored` / `deferred` receipt), never blocking the lifecycle. A `set-tracker-id` collision is handled exactly as the link ceremony (Phase 2): ask the user (interactive) or `sync defer` (Ralph) — never `--force` silently.

**Always snapshot the merge base at create time — even when the triggering op is `comment`.** The `comment` path leaves body/status untouched and seeds no base of its own, and `reconcile` on a brand-new issue echo-fences to a noop, so the **auto-create** step is the only place the base gets written on a `comment`-first (or `reconcile`-first) auto-link. The issue body we just wrote *is* the `renderFlowToTracker` output, so both base halves are exact at that instant. Skip this and a `comment`-first auto-create leaves the linked issue **base-less** until some later body sync; the no-base bootstrap then treats that sync as a fast-forward projection and can silently **overwrite tracker-side edits** made after the issue was created. (`push`-first auto-link is unaffected either way — the `push` skeleton below re-snapshots the base after writing; the create-time snapshot just makes the `comment`/`reconcile`-first paths match.)

Route the operation; each layer calls hooks that operate on the normalized structs ([`references/adapter-interface.md`](references/adapter-interface.md)). The skeleton is real; the hook bodies plug in later. The **Linear transport hooks** (`fetchIssue`/`writeIssue`/`listComments`/`postComment`/`readStatus`/`setStatus`) are implemented by the detect-best-available ladder in [`references/linear-ladder.md`](references/linear-ladder.md) (MCP → GraphQL → no-op); GitHub's are the `gh` transport in [`references/github.md`](references/github.md) (single rung + no-op, reduced-fidelity status — fn-52.7); GitLab's are the `glab` transport in [`references/gitlab.md`](references/gitlab.md) (`glab` CLI → raw-REST token fallback → no-op, reduced-fidelity status — fn-69); Jira's are the REST transport in [`references/jira.md`](references/jira.md) (Cloud `/rest/api/3` + ADF → DC/Server `/rest/api/2` → no-op, workflow-aware status via the transitions API — fn-70). The **body hooks** (`renderFlowToTracker` / `foldTrackerIntoFlow` / `threeWayMergeBody`) are the agentic 3-way merge + format translation in [`references/body-merge.md`](references/body-merge.md) (fn-52.4); the **status who-wins** hook (`reconcileStatus`) is [`references/status-sync.md`](references/status-sync.md) and the **comments/evidence append + dedup** hooks (`postLifecycleComment` / `pullCommentsToSyncLog`) are [`references/comments-sync.md`](references/comments-sync.md) (fn-52.5).

```
push(spec):
 prEvidence = mergeEvidenceProbe(spec.branch_name) → status-sync.md (merged|open|closed-unmerged|none|ambiguous|probe-error)
 body = renderFlowToTracker(spec) → body-merge.md Step 3 (flow→tracker) — COMPLETE spec, ALL sections; never summarize/truncate
 writeIssue(issue{... body ...}) [→ ref: transport] # A full-body UPDATE on an adapter that carries the <!-- flow:deps --> block (GitHub on its fenced fallback; GitLab on EVERY tier — native is_blocked_by AND degraded relates_to) preserves the flow-owned region (github.md / gitlab.md § writeIssue) — body=renderFlowToTracker output never contains it, so a raw full-body replace would wipe it and make projectDepRelations misread the ledgered edge as a remote removal → false collision. Write retains; merge strips (body-merge.md Step 0.5).
 setStatus(flowToNormalized(spec, prEvidence) → tracker status) → status-sync.md (who-wins)
 # MERGE-EVIDENCE GATE (fn-66): the terminal rung (done/verified) is reachable
 # ONLY when prEvidence == merged. flowToNormalized refuses terminal for
 # none/open/closed-unmerged/ambiguous/probe-error — so NO push (automatic land.merged
 # OR a manual reconcile) ever writes Done without a GitHub MERGED probe. The gate is a
 # per-WRITE invariant (status-sync.md): a manual merge-evidenced push MAY terminal-write;
 # a local-completion-only push never does.
 postComment(lifecycle event marker) → comments-sync.md (append + dedup)
 projectDepRelations(spec, issue) → § projectDepRelations below — depends_on_epics → blocked-by relations (additive, ledger-tracked, never advances lastSyncedAt; warns on unlinked dep; skipped when no transport)
 sync set-merge-base (BOTH halves) + set-last-synced # snapshot the pushed pair (body-merge.md Step 5)
 receipt: pushed

pull(spec):
 issue = fetchIssue(trackerId) [→ ref: transport] → normalized issue
 comments= listComments(trackerId) [→ ref: transport] → normalized comment[]
 status = readStatus(trackerId) [→ ref: transport] → normalized status
 foldTrackerIntoFlow(spec, issue, status) → body-merge.md Step 3 (tracker→flow) + status-sync.md (who-wins) + comments-sync.md (pull genuine comments to sync log)
 # echo-fence first: pulled body hash == baseHashTracker ⇒ noop (body-merge.md Step 1 / Fixture D)
 projectReadiness(spec, issue) → status-sync.md § Readiness projection — tracker.readyState → local `ready` flag (skipped when readyState null; change-only receipt; one-way pull)
 receipt: pulled | noop

comment(spec): # lifecycle touchpoint (work.done / resolvePr / completionReview / qa)
 postLifecycleComment(spec, event marker + evidence) → comments-sync.md (append + dedup) [→ ref: transport: postComment]
 # body + status untouched; create-if-unlinked already linked + base-snapshotted an unlinked spec before we got here
 receipt: updated | noop
```

For the **reconcile** path, the orchestration delegates the full 3-way merge to
[`references/body-merge.md`](references/body-merge.md) (fn-52.4) — it is no longer a
stub. The skeleton's job is to fetch the three inputs, hand them to the merge, and
route the result to the receipt / defer / write-back; the merge logic (pre-reduction,
agentic both-sides-diverged judgment, format translation, structural gate, scoped
conflict) lives in that reference:

```
reconcile(spec):
 base = sync get-state → merge-base snapshot (BOTH forms: mergeBaseFlow + mergeBaseTracker)
 issue = fetchIssue(trackerId) [→ ref: transport]
 prEvidence = mergeEvidenceProbe(spec.branch_name) → status-sync.md (feeds reconcileStatus; gates terminal)
 projectReadiness(spec, issue) → status-sync.md § Readiness projection (rides every issue read; independent of the body merge — runs even when the body diverges)
 projectDepRelations(spec, issue) → § projectDepRelations below (rides every issue read like projectReadiness; independent of the body merge — runs even when the body diverges or conflicts)
 merged = threeWayMergeBody(base, flowBody, issue.body) → body-merge.md
 # Step 1 pre-reduce: echo / byte-identical / only-one-side-changed ⇒ auto (no conflict)
 # Step 2 agentic merge (both diverged) + Step 3 format translation + Step 3.5 structural gate
 if genuine conflict (body-merge.md Step 4):
 interactive → show merged body, confirm the ONE scoped section before write-back (plain-text numbered prompt)
 Ralph → sync defer (queue the scoped conflict, never block) [R9/R11]
 receipt: diverged
 else:
 writeIssue(merged) + setStatus(reconcileStatus(spec, issue, prEvidence)) [transport → fn-52.3/.7] + status-sync.md (who-wins)
 # MERGE-EVIDENCE GATE (fn-66): reconcileStatus runs flowToNormalized(spec, prEvidence)
 # first — a manual reconcile MAY terminal-write Done/verified IFF prEvidence == merged
 # (status-sync.md S-I); closed-unmerged/ambiguous/probe-error → in-review + NEEDS_HUMAN
 # (S-J), none → preserve non-terminal (S-G). The terminal-write merge-evidence invariant
 # holds on this manual path exactly as on the automatic land.merged touchpoint.
 sync set-merge-base (BOTH halves) + sync set-last-synced # body-merge.md Step 5 — ONLY on success
 receipt: merged | updated
 # no-base bootstrap (first link): body-merge.md "First-sync / no-base bootstrap" —
 # flow-first ⇒ fast-forward projection; tracker-first ⇒ seed base, pull-only. Never a conflict.
```

### `projectDepRelations(spec, issue)` — project `depends_on_epics` as blocked-by relations (fn-64, R3/R4/R5/R6/R8/R10)

**Transport-blind, one-way, additive.** This hook projects the spec's *local* dependency graph onto the tracker. It rides **both** the `push` and `reconcile` paths (modelled on `projectReadiness` [→ ref: status-sync.md § Readiness projection]): change-only receipts, **never advances `lastSyncedAt`** by itself, never blocks the lifecycle. The skill resolves edges and drives the normalized `listIssueRelations` / `setIssueRelation` transport pair ([→ ref: adapter-interface.md § Relation transport]) — it **never branches on per-tracker (Linear / GitHub / GitLab / Jira)** (R8); each adapter ([→ ref: linear-ladder.md / github.md / gitlab.md / jira.md]) implements its own fidelity. No transport reachable (`TRANSPORT=none`) ⇒ skip the whole hook, write **one** `noop` receipt, return (never a crash, never a block).

**Enumerate edges from flowctl (the deterministic half).** `depends_on_epics` is read for you; do NOT parse the spec yourself:

```bash
EDGES=$($FLOWCTL sync list-dep-relations "$SPEC_ID" --json)
# → .depRelations[] = [{dep_spec, dep_tracker_id, dep_identifier, dep_status, projected}]
# dep_tracker_id null ⇒ the dep spec is NOT linked to any issue (missing-link warning)
# dep_status ⇒ the LOCAL dep-spec status (done/open/…), flow-authoritative — NOT a remote fetch
# projected: true ⇒ already in the depRelations ledger (idempotent re-run target)
```

For each edge, in order:

1. **Missing dependency link (R4).** `dep_tracker_id == null` ⇒ the dep spec isn't linked. **Warn naming the dep spec id + the parent**, surface it on the receipt with the fn-57 grammar, and **continue** (item-level isolation — one unresolvable dep never aborts the rest):
 ```bash
 $FLOWCTL sync receipt "$SPEC_ID" --status noop --transport "$TRANSPORT" ${EVENT:+--event "$EVENT"} \
 --note "operation: projectDepRelations $SPEC_ID, event: ${EVENT:-manual} — dependency spec <dep_spec> has no tracker link; relation skipped, sync continues"
 ```
 The warning line ALSO appears in the skill's human-facing report. Never silently drop an unlinked dep.

2. **Self-edge (R8).** The resolved dep issue is the **same** issue as the current spec's (`dep_tracker_id == this spec's tracker.id`) ⇒ **skip with a warning** — never project an issue blocked by itself. (flowctl already rejects a self `dep_spec` at `set-dep-relation`; this guard catches the rare case where two specs resolve to the *same* issue.)

3. **Resolved edge ⇒ project the blocked-by relation (R3/R8).** Drive the transport with **read-before-write** dedup baked into the adapter (`listIssueRelations` first — neither platform reliably no-ops a duplicate). The direction is anchored once in adapter-interface.md: `setIssueRelation(issue = this spec's issue, blockedBy = dep issue)`:
 ```bash
 setIssueRelation(issue=$ISSUE, blockedBy=$DEP_ISSUE) [→ ref: linear-ladder.md / github.md / gitlab.md / jira.md]
 ```
 On a successful **new** create, record provenance in the ledger so the rerun is idempotent and removal stays provably-ours-only (R6/R7):
 ```bash
 $FLOWCTL sync set-dep-relation "$SPEC_ID" --dep-spec "$DEP_SPEC" \
 --from-tracker-id "$ISSUE_ID" --to-tracker-id "$DEP_ISSUE_ID" # type=blocks, source=flow (defaults)
 ```
 An adapter `noop` (edge already present) writes nothing new; a `set-dep-relation` is itself idempotent (dedup no-op) so a redundant call is harmless. **Cycles (R8): NO graph traversal.** Each `depends_on_epics` edge is projected as an independent direct relation; a cycle in the flow graph is tolerated (each declared edge stands alone — never expand transitively).

4. **Completed blocker (R5).** `dep_status == "done"` ⇒ the dep is a **historical/completed blocker**. **Keep the relation visible** (still project it / leave it in place — a closed blocker on the board is real audit history) but it must **NOT feed `ready=true` gating** — readiness (fn-58) already treats done deps as satisfied, and this hook **never** touches the `ready` flag (no `spec ready`/`unready` call here). Keying off the **local** `dep_status` (not a remote status fetch) is what keeps this from regressing fn-58.

**Never-clobber + who-wins collision (R6/R10).** `setIssueRelation` is **strictly additive** — it only ever *creates* the blocked-by edge, never deletes. A relation not in our `depRelations` ledger (native) / outside the `<!-- flow:deps -->` fence (GitHub's fenced fallback; GitLab's block on every tier) is **never ours** and is left untouched. The one reconcile case that needs judgment is the **collision** — and it is evaluated **BEFORE** any per-side add/keep rule (memory: who-wins-ladder-must-check-collision-first — order the both-match branch first or the earlier single-field rule silently wins):

> **Collision:** an edge present in the `depRelations` ledger AND still in Flow's `depends_on_epics`, but **MISSING as a tracker-visible link** — `listIssueRelations` either doesn't return it OR returns it `linkPresent:false` (on GitLab a `source:"block-only"` entry: the `<!-- flow:deps -->` block still records the edge but the native `is_blocked_by` / degraded `relates_to` link is gone). A tracker user removed the relation flow projected. **Branch on `linkPresent`, never bare membership** — the flow block alone is provenance, not tracker presence (gitlab.md § listIssueRelations).

Re-creating it silently would steamroll a deliberate human removal (the explicit anti-behavior). So **defer + `queued`, never silently recreate**:

```bash
$FLOWCTL sync defer "$SPEC_ID" \
 --summary "Projected blocked-by relation (<dep_spec>) removed on the tracker but still declared in depends_on_epics" \
 --suggested "Human: re-add the relation, or drop <dep_spec> from depends_on_epics" \
 --reason "dep-relation-collision"
$FLOWCTL sync receipt "$SPEC_ID" --status queued --transport "$TRANSPORT" ${EVENT:+--event "$EVENT"} \
 --note "operation: projectDepRelations $SPEC_ID, event: ${EVENT:-manual} — ledgered relation <dep_spec> missing remotely; queued, not recreated"
```

In Ralph/autonomous mode this is already the behavior ("ask the human" resolves to "queue for the human", Phase 0). Interactive mode MAY additionally surface the choice via `plain-text numbered prompt`, but the conservative default — **queue, do not recreate** — holds either way.

**Fenced-block ↔ body-merge ownership (R10 — fn-64.5 owns this rule).** The relation lives in a flow-owned `<!-- flow:deps -->` … `<!-- /flow:deps -->` body block on **GitHub's fenced fallback** (native dependencies unavailable) and on **GitLab on every tier** — GitLab carries the block as the durable direction/provenance source on BOTH the native `is_blocked_by` path AND the Free/personal `relates_to` degrade ([→ ref: github.md / gitlab.md § setIssueRelation]). That block is **flow's, not the spec's** — the body-merge layer MUST exclude it from divergence detection so a reconcile never folds flow's own dependency block back into the spec and render never overwrites it. This is the canonical **tracker-body-for-merge** transform: strip the fenced region BEFORE every `baseHashTracker` / `mergeBaseTracker` / fetched-`issue.body` comparison, and reinject/preserve it on every issue-body write for an adapter that carries the block (GitHub fenced fallback; GitLab every tier). See [→ ref: body-merge.md § Flow-owned fenced regions]. Raw full-body hashing would flag the block as tracker divergence and break echo-suppression — the strip happens at the **hash boundary**, not just visually.

**Receipts (use the real enum).** Every projectDepRelations outcome ends in a receipt whose status ∈ `{updated, noop, queued, errored}` (NO "deferred" — not in the enum): a new relation created ⇒ `updated`; nothing to do / already-projected / no-transport / missing-link ⇒ `noop`; collision deferred ⇒ `queued`; a genuine transport failure (not a 404-style absent issue) ⇒ `errored`. Lifecycle runs carry `--event` (`${EVENT:+--event "$EVENT"}`); the note uses the fn-57 `operation: projectDepRelations <id>, event: <key>` grammar verbatim. A relation receipt **never advances `lastSyncedAt`** — like readiness, this is a one-way projection that rides the sync, not a body reconciliation.

**Echo-loop suppression** (constraint): after a push, record the resulting tracker-side content hash; on the next pull a hash match = flow's own echo ⇒ `noop`, never a phantom conflict. `lastSyncedAt` advances only on a real reconciliation, never on a no-op pull. The hash bookkeeping rides on the merge-base snapshot (fn-52.4).

**Failure handling** (constraints): a 404 / archived / deleted linked issue does NOT crash, does NOT clear state or advance `lastSyncedAt` — emit an `errored` receipt and prompt/queue an unlink decision. Batch sync is item-level: one spec's failure gets its own `errored` receipt + no state write, and the run continues.

Every operation ends with a receipt:

```bash
$FLOWCTL sync receipt "$SPEC_ID" --status pushed --tracker-id "$ISSUE_UUID" --transport "$TRANSPORT" ${EVENT:+--event "$EVENT"} --note "..."
# status ∈ {pushed,pulled,merged,updated,diverged,queued,errored,noop}; --transport ∈ {mcp,graphql,gh,glab,rest,none}
# --event tags the lifecycle touchpoint served (Phase 0); empty EVENT (manual run) omits the flag
# --merges-file records body-merge records for audit/rollback (fn-52.4 supplies it)
```

## Phase 4 — Genuine conflict (scoped) — body-merge.md Step 4

Only a genuine semantic contradiction the agent can't confidently resolve is surfaced — **scoped to the section**, never the whole body, never a silent overwrite. Interactive: show the merged body for confirmation before write-back. Ralph/autonomous: queue.

```bash
$FLOWCTL sync defer "$SPEC_ID" --summary "Goal section rewritten on both sides to mean different things" \
 --suggested "Human picks: keep flow's framing, the tracker's, or a merge" --reason "genuine-contradiction"
```

The decision flow and the structural gate (no section silently dropped; both sides' non-conflicting additions present) live in [`references/body-merge.md`](references/body-merge.md) (fn-52.4, Steps 3.5 + 4). The skeleton wires the `sync defer` queue + the interactive `plain-text numbered prompt` confirmation entry point; the merge reference owns the judgment of *what* is a genuine, section-scoped contradiction (vs an additive change both sides keep).

## Phase 5 — Unlink / teardown

Unlinking clears tracker id + `lastSyncedAt` + merge-base atomically and posts a one-line "detached" comment to the issue. A re-link re-seeds the base (does not resurrect stale state).

```bash
# 1. post the detached comment FIRST (best-effort; a failed comment must not block the unlink)
postComment(trackerId, "Detached from flow spec <id> on $(date -u +%Y-%m-%d).") [transport → fn-52.3/.7]
# 2. wipe state atomically
$FLOWCTL sync clear "$SPEC_ID"
$FLOWCTL sync receipt "$SPEC_ID" --status updated --note "unlinked from tracker" # no --event: unlink is a manual ceremony, never a lifecycle touchpoint (Phase 0)
```

`sync clear` is atomic (fn-52.1) — it wipes the tracker id, `lastSyncedAt`, and the merge-base snapshot together. The id/branch/files of the spec are NEVER touched (no rename on unlink).

## Phase 6 — Listings (surface `identifier`)

When listing sync state, surface the tracker `identifier` (display form, e.g. `WOR-17`) alongside the flow id so users see both handles:

```bash
$FLOWCTL sync list-unsynced --json # specs needing a first push
$FLOWCTL sync list-stale --json # linked specs with old/missing lastSyncedAt (default tracker.staleAfterHours)
$FLOWCTL sync get-state "$SPEC_ID" --json # one spec's full state (tracker id + identifier + url + base)
```

For each linked spec, render a line like `wor-17-slug ↔ WOR-17 (linked, synced 3h ago)` or `fn-42-foo ↔ WOR-99 (alias, stale)`. The flow id is the canonical handle; `identifier` is the board-facing display form.

## Phase 7 — Backlog-mode ops (`list-open` / `list-relations` / `question`) — fn-68 R14/R15

Three **skill-level, transport-blind** named ops that pilot's autonomous backlog scheduler invokes. They route through the same adapter ladder (`listOpenIssues` / `listIssueRelations` / `listComments` / `postComment` **[→ ref: linear-ladder.md / github.md / gitlab.md / jira.md]**) as every other op — pilot never calls a tracker-specific API and **never** calls flowctl for transport (flowctl has no tracker transport; architecture rule). `list-open` and `list-relations` are **read-only** (they never write to the tracker); `question` writes a comment. All run under the **autonomy gate** (Phase 0) — `question` authoring resolves "ask the human" to a queued/best-effort post, never `plain-text numbered prompt`.

### 7a — `list-open` — enumerate the promoted-lane open issues

Unions in the **tracker-side** open issues that have no flow spec, so backlog mode can triage tickets `flowctl specs` can't see. It is the skill's half of the union (`flowctl ready --all` supplies the flow-side specs; this op supplies the tracker-side items).

```
list-open:
 if tracker.readyState is unset:
 # No promoted-lane filter exists — readiness setup is optional and was skipped.
 # NO-OP WITH A NOTE (fn-68): backlog mode then runs the flow-ready specs ONLY
 # (the flow `ready` flag needs no tracker). Never enumerate the whole issue history.
 receipt: noop --note "list-open: tracker.readyState unset — no promoted lane to enumerate; flow-ready specs only"
 return [] # empty list, not an error
 issues = listOpenIssues({ readyState: <tracker.readyState> }) [→ ref: transport]
 # EXACT-match filter: lists ONLY issues at the exact readyState state (Linear) /
 # carrying the exact readyState label (GitHub or GitLab). readyState matching is exact —
 # no state ordering exists, so NO "beyond"/"and-later" lane is inferred (fn-68).
 → normalized issue[] (transport-blind structs — pilot reads {id, identifier, title, status, labels, url})
 receipt: noop --note "list-open: <N> open issues at readyState '<configured>'" # a read-only enumeration never advances lastSyncedAt
```

- **`tracker.readyState` unset ⇒ no-op + note, return `[]`** (NOT an error). No promoted lane exists to filter on, so backlog mode falls back to the flow-ready specs only.
- **Exact-match, bounded.** `listOpenIssues` lists issues at the **exact** `tracker.readyState` state/label — never "beyond" it (no state ordering exists; an ordered promoted-set is a future config, never inferred). It is the promoted lane, not the whole backlog.
- **Transport-blind.** Pilot consumes the normalized `issue[]`; it never branches on per-tracker (Linear / GitHub / GitLab / Jira). The adapter (`listOpenIssues` in [`references/linear-ladder.md`](references/linear-ladder.md) / [`references/github.md`](references/github.md) / [`references/gitlab.md`](references/gitlab.md) / [`references/jira.md`](references/jira.md)) owns the wire query.
- **No-transport ⇒ `noop` + note, `[]`** — same documented no-op floor as the other methods.

### 7b — `question <spec-id | tracker-id>` — post a question-valve comment

The `ask` stage's tracker side: post an Open Question to the issue behind the **stable anchor** (R15), so a re-triage never re-posts and a human reply round-trips back. Resolves the subject by id form:

- **spec-backed** (`question <spec-id>` resolving to a linked spec) — the question's durable parked state lives in the spec's `## Open Questions` (the answer-import path below folds the reply there). The tracker comment is the mirror.
- **tracker-only** (`question <tracker-id>`, an issue with no flow spec — a promoted ticket backlog mode surfaced via `list-open`) — there is no spec to anchor in, so the **parked state lives in the tracker**: the question comment's `status=open` anchor + a matching `<!-- flow-next:answer id=… -->`, detected by scanning the issue comments. **No spec import/flip happens until capture/interview later creates a spec.**

**Build the stable anchor — hash STABLE fields only:**

```
id = hash( subjectId + "\0" + blockedStage + "\0" + reasonCode + "\0" + questionSlug )
 # subjectId = the SPEC ID when spec-backed, else the opaque TRACKER ID (UUID) — tracker-only
 # items have no spec id. NEVER a bare tracker issue KEY (WOR-17 / #123) — Linear
 # auto-linkifies keys even inside HTML comments, mangling the anchor.
 # blockedStage = the pilot stage that blocked (e.g. plan / work / review).
 # reasonCode = a stable enum slug (e.g. needs-spec / ambiguous-ac / dep-unsatisfied).
 # questionSlug = a short stable slug of the question (NOT the free prose).
 # The free-prose reason text is OUTSIDE the hash — rephrasing the question NEVER spawns a
 # duplicate anchor (same id ⇒ comments-sync dedup skips the re-post).
```

Post the comment (the anchor is the first line, then the free-prose question + the `capture`/`interview` pointer):

```markdown
<!-- flow-next:question id=<hash> status=open -->

**flow-next needs a human** — <blocked stage>: <free-prose reason / question>.

Run `/flow-next:capture` or `/flow-next:interview` to resolve, or reply here with `<!-- flow-next:answer id=<hash> -->`.
```

```
question(subject):
 resolve subjectId:
 spec-backed → subjectId = <spec-id>; parkedHome = spec ## Open Questions (mirror in tracker)
 tracker-only → subjectId = <tracker UUID>; parkedHome = the tracker (no spec yet)
 id = hash(subjectId, blockedStage, reasonCode, questionSlug) # stable fields only
 existing = listComments(trackerId) # normalize <issue …>KEY</issue> → KEY first
 if any comment carries `flow-next:question id=<id>`: skip (already parked) # comments-sync dedup by id
 else: postComment(trackerId, anchor + question body) [→ ref: transport]
 spec-backed → ALSO write the `<!-- flow-next:question id=<id> status=open -->` anchor under the
 spec `## Open Questions` (the durable flow-side park).
 receipt:
 spec-backed → sync receipt <spec-id> --status updated (the normal spec-id-keyed sync receipt)
 tracker-only → NO spec-id sync receipt (there is no spec id to key on — fn-68): the audit trail is
 the pilot-log row + the tracker comment anchor itself. Emit at most a noop note.
```

- **Idempotent by `id`.** Re-triaging the same blocked subject computes the same `id` (the prose is outside the hash) → comments-sync's marker dedup (`comments-sync.md` Layer 1, keyed on `flow-next:question id=`) finds the existing comment → **skip the re-post**.
- **No bare issue key in the anchor.** `subjectId` is the spec id or the opaque UUID — never `WOR-17` / `#123` (linkify hazard, same mitigation as the `flow-next:sync` marker keying on `issue=<uuid>`).
- **Tracker-only `question` is exempt from the spec-id sync receipt** (fn-68): there is no spec id to key a receipt on. Its parked/answered state is detected by **scanning the tracker comments** for `flow-next:question id=… status=open` + a matching `flow-next:answer id=…` — no spec anchor required, no import/flip until a spec exists.
- **Selection skips a parked subject.** Backlog selection (in .3/.4) checks the parked home — the spec `## Open Questions` (spec-backed) or the tracker comments (tracker-only) — and **skips any subject carrying a `status=open` parked question**, so it is never re-picked every tick.

### Answer round-trip (R15) — import a matched reply, flip the anchor

The answer is detected on the **next pull/reconcile** (rides the existing `listComments` path) from **either** side:

1. **Spec anchor flipped by a human** — a human edits the spec `## Open Questions` anchor to `status=answered` with the answer prose. The next tick re-triages the now-answered item and proceeds.
2. **Tracker reply matched by `id`** — the answer comment carries `<!-- flow-next:answer id=<hash> -->`. Match it to the open question by `id`:
 - **Threaded tracker (Linear)** — the normalized `comment` carries optional **reply/parent metadata** ([→ ref: adapter-interface.md § `comment`]); a reply *under* the question comment is matched by thread + `id`.
 - **Flat tracker (GitHub / GitLab / Jira — no threads)** — there is no parent link, so the **`<!-- flow-next:answer id=<hash> -->` marker is the load-bearing match**: the answer is matched to the question **by `id` regardless of threading**.
3. **Answer authority (security — the marker `id` is necessary, NOT sufficient).** Honor a `flow-next:answer` marker **only from an authorized commenter** — anyone with tracker comment access could inject the marker, so validate `comment.author` before treating the question as answered:
 - **`comment.authorAuthority == "writer"`** — the adapter resolves the author's permission tier into the normalized `comment` field ([→ ref: adapter-interface.md § `comment`]: GitHub from `author_association`, Linear from team membership). Never an `outsider` drive-by commenter, never a `bot` (except flow's own automation marker), and never `unknown` (the transport couldn't resolve it ⇒ **fail closed**); **AND/OR**
 - the author is in the optional `tracker.answerAuthors` allowlist (issue assignee / named approvers) when configured.
 An answer marker from an **unauthorized** author is **ignored** — the question stays `status=open` and the run emits a receipt note (`answer id=<id> from unauthorized author <login> — ignored`). The spec-anchor path (1) already carries its own authority (the human edits the spec in a **commit**, gated by repo write access); this guard closes the weaker tracker-comment path.

```
on pull/reconcile, for each open question (spec ## Open Questions, or tracker comments for tracker-only):
 ans = find a comment carrying `flow-next:answer id=<id>` FROM AN AUTHORIZED AUTHOR # marker id + author-authority (security); unauthorized markers are ignored, question stays parked
 if ans found AND subject is spec-backed:
 import ans.body UNDER the matching `## Open Questions` entry by `id` # NOT only into ## Sync Log
 flip that anchor: status=open → status=answered
 receipt: updated --note "answer imported for question id=<id>; flipped to answered"
 if ans found AND subject is tracker-only:
 leave it in the tracker (no spec to import into); the status=open + matching answer is the durable record.
 A later /flow-next:capture or /flow-next:interview creates the spec and folds the Q+A then.
 else: stays parked (status=open) — selection keeps skipping it next tick.
```

- **Import target is the matching Open Question, not just the Sync Log.** A matched answer folds **under the `## Open Questions` entry keyed by `id`** (and flips that anchor to `answered`), so the question and its answer live together — distinct from a genuine tracker comment, which still appends to `## Sync Log` per comments-sync.
- **Answer matching is `id`-keyed on both rungs.** Threaded (Linear reply/parent metadata) OR flat (GitHub / GitLab / Jira `<!-- flow-next:answer id= -->` marker) — the `id` is the join key either way, so a flat tracker's answer round-trips exactly like a threaded one.

### 7c — `list-relations <tracker-id>` — read one issue's dependency relations

The **dep-edge READ** backlog mode's selection (pilot `workflow.md` Phase 1.5e / `references/backlog-mode.md` Phase 1e) needs to dep-order the tracker-side candidates. `list-open` returns issues only (no relations), so for each **tracker** candidate this op reads its `relation[]` edges via the existing `listIssueRelations` adapter method (fn-64) — the SAME read `projectDepRelations` already uses, surfaced as a standalone backlog-mode op. **Read-only — it never writes a relation** (that is `setIssueRelation`, push/reconcile only), so it is safe to call per-tick under the autonomy gate and is on pilot's dispatch allowlist (a READ, never a merge). (GitLab note: the adapter resolves the issue API path `iid` from the candidate's normalized `identifier` — the `listOpenIssues` `issue.identifier` for a tracker-only candidate, or the stored `tracker.identifier` for a spec-backed one — never the global id; gitlab.md § identity. A bare global id cannot index GitLab's `/projects/:id/issues/:iid` path.)

```
list-relations(trackerId):
 rels = listIssueRelations(trackerId) [→ ref: transport]
 # normalized relation[] — {from = blocked, to = blocker, type}; transport-blind
 → return rels # pilot normalizes `from`/`to` into topo-sort edges (blocked ← blocker)
 receipt: noop --note "list-relations: <N> relation(s) for <trackerId>" # a read-only enumeration never advances lastSyncedAt
```

- **Transport-blind.** Pilot consumes the normalized `relation[]`; it never branches on per-tracker (Linear / GitHub / GitLab / Jira). The adapter (`listIssueRelations` in [`references/linear-ladder.md`](references/linear-ladder.md) / [`references/github.md`](references/github.md) / [`references/gitlab.md`](references/gitlab.md) / [`references/jira.md`](references/jira.md)) owns the wire query.
- **No-transport / no-relations ⇒ `noop` + note, `[]`** — same documented no-op floor as `list-open`; selection then dep-orders on the flow `blockedBy` edges alone.
- **Read-only.** This op NEVER drives `setIssueRelation` — it only reads. Relation *projection* (writes) stays on the `push` / `reconcile` `projectDepRelations` path, never on a backlog-mode tick.

## Boundaries (repeat — load-bearing for this scaffold)

- Hook bodies marked **[→ ref: <file>]** are NOT inlined here — this file routes; read the referenced file for the body. Transports live in `linear-ladder.md` / `github.md` / `gitlab.md` / `jira.md`; reconcile in `body-merge.md` / `status-sync.md` / `comments-sync.md`.
- `set-merge-base` always writes BOTH halves (paired-snapshot invariant).
- Receipts on every run — event-tagged on lifecycle runs (`${EVENT:+--event "$EVENT"}`, Phase 0); conflicts queue (`sync defer`), never block (R11).
- **Autonomy parity (fn-68 R14):** the Phase-0 `RALPH` gate recognizes the full marker family (`FLOW_RALPH` / `REVIEW_RECEIPT_PATH` / `FLOW_AUTONOMOUS` / `mode:autonomous`); under it NO path reaches `plain-text numbered prompt` — every "ask the human" resolves to `sync defer`.
- **Backlog-mode ops (fn-68, Phase 7):** `list-open` + `list-relations` + `question` are skill-level + transport-blind (never flowctl transport). `list-open` / `list-relations` are READ-only (no tracker write); `list-open` no-ops with a note when `tracker.readyState` is unset; `list-relations` no-ops when no transport / no relations; a tracker-only `question` is exempt from the spec-id sync receipt and parks in the tracker.
