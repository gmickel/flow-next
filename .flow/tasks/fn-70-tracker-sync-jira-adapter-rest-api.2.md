---
satisfies: [R1, R2, R6, R8, R9]
---
## Goal
Author `references/jira.md` transport + core: the **Jira REST API + token single-rung + no-op** transport (GitHub-shaped — NO MCP rung; Cloud `/rest/api/3` + API-token, DC/Server `/rest/api/2` + PAT), the six core methods, auth (Cloud basic vs DC Bearer PAT + self-hosted TLS), identity, and the make-pr PR-link. Records the MCP-evaluated-not-wired decision + evidence. Modeled on `github.md`. (Spec R1-core, R2, R6-link.)

## Files
- `plugins/flow-next/skills/flow-next-tracker-sync/references/jira.md` (new) — authored from `github.md` (single-rung + no-op discipline).
- Reads: `adapter-interface.md`.

## Approach — auth + endpoints verified live 2026-06-28 (`~/work/agent-scripts/flow-smoke/out/FINDINGS-jira.md`)
- **Transport** (cf. github.md rung detection): the Jira REST API — **`baseUrl = JIRA_BASE_URL || tracker.perTracker.baseUrl`** (env overrides the persisted config), credentials from env per persisted `authScheme` (Cloud v3 / DC v2 per `apiVersion`) → no-op. **No MCP rung** — record the decision in-doc: official Atlassian MCP can't transition/update/link (read-mostly); community MCP is a redundant PAT-wrapper. Transport resolved once at the ceremony (fn-70.1), persisted; runtime = cheap credential-presence check → no-op (never a support-probe).
- **Auth + endpoint family (verified Cloud):** read the persisted `authScheme`/`apiVersion` (fn-70.1) — **Cloud** = basic `email:API_TOKEN` over **`/rest/api/3`** (`JIRA_EMAIL`+`JIRA_API_TOKEN`, confirmed working); **DC/Server** = Bearer PAT (`JIRA_PAT`) over **`/rest/api/2`**, body format may differ — **branch on `apiVersion`; DC deltas are verify-at-build** (no DC instance validated). Label unambiguously (Cloud has no "PAT"). Self-hosted TLS opt-in `JIRA_SSL_VERIFY=false`. Never store creds in flow state.
- **Core six** (paths use Jira's `{issueIdOrKey}` — **prefer the persisted durable `tracker.id`** at runtime, not the mutable key; refresh `identifier` from each fetch response): `POST /issue` (ADF description + labels — colon labels like `flow:<id>` accepted), `GET /issue/{issueIdOrKey}`, `PUT /issue/{issueIdOrKey}` (ADF body), `GET`/`POST /issue/{issueIdOrKey}/comment` (ADF), `GET /issue/{issueIdOrKey}` status. **`comment.author.accountType`** → `authorAuthority` (app⇒bot, customer⇒outsider; **`atlassian` is NOT auto-`writer`** for the answer valve — gate `writer` on a project-role/group check or `tracker.answerAuthors`, else **`unknown`/fail-closed** — the enum is `writer|outsider|bot|unknown`, no new value; fn-68 contract). Transitions detail → fn-70.3.
- **Identity:** durable `tracker.id` = the **immutable Jira issue `id`**; the display `key` `PROJ-123` (mutable) is the `identifier` — the link flow accepts a `key`, **resolves it to the `id` via `GET /issue/{key}`**, persists the `id`. Back-reference labeled marker + body anchor.
- **make-pr PR↔issue link:** **Cloud v3 (verified):** `POST /rest/api/3/issue/{issueIdOrKey}/remotelink {object:{url,title}}` (HTTP 201); **DC/Server v2:** `/rest/api/2/issue/{issueIdOrKey}/remotelink` (verify-at-build) — branch on `apiVersion`; no auto-linkify / `gh`.
- "enterprise teams", not "portco".

## Acceptance
- REST-only single-rung + no-op documented; **MCP-not-wired decision + evidence recorded** (R2).
- Six core methods with concrete Jira REST calls (Cloud v3 / DC v2); `authorAuthority` from `accountType` + project-role gate (R1-core).
- Auth split (Cloud basic / DC Bearer PAT) + TLS labelled (R2 / R9 auth).
- PR-link as `remotelink` (R6-link).
- Canonical Claude names.

## Test notes
- Reference doc — prose contract + read-through; testable bits in fn-70.1, mirror in fn-70.4. Auth + remote-link already smoke-tested live.

## Description
TBD

## Done summary
Authored `references/jira.md` — the Jira REST-API single-rung transport doc: the six core methods (fetchIssue/writeIssue/listComments/postComment/readStatus/setStatus) over `/rest/api/{3|2}`, the two auth schemes (Cloud cloud-basic email:API_TOKEN over v3, DC/Server bearer-pat JIRA_PAT over v2) with opt-in self-hosted TLS, the immutable-`id`-vs-mutable-`key` identity model, the normalized-struct firewall, and the in-adapter make-pr remote-link. Records the MCP-evaluated-not-wired decision + evidence (NO MCP rung) and defers ADF translation / transitions-status / relations / listOpenIssues to fn-70.3 with explicit boundary pointers.
## Evidence
- Commits: d7856a62422a1bc5fb2c4f7183574785842b9910
- Tests: uv run python -m pytest plugins/flow-next/tests/test_tracker_sync_jira.py (32 passed), full tracker-sync suite: 215 passed, 39 subtests (test_tracker_sync_{jira,gitlab,state,backlog_mode,mirror_parity},test_tracker_id_{generator,resolution},test_tracker_config,test_tracker_receipts,test_land_tracker_event,test_qa_tracker_event)
- PRs: