# Tracker-sync determinism: flowctl owns the wire, skills own judgment

## Goal & Context
<!-- scope: business -->

Tracker-sync is **476,883 characters of prose** describing API calls. `github.md`, `gitlab.md`, `jira.md` and `linear-graphql.md` alone contain **112 literal invocations** (`gh api`, `glab api`, `curl -sS`) written out in English. That is code. It is simply written in a language that cannot be executed, type-checked, or unit-tested.

The cost of that is measured, not theoretical. PR #241 took **22 cross-model review waves**, and every single bug found was deterministic:

- an `else` branch that could never be reached, so spec creation aborted when no transport was reachable
- the recovery record cleared before the back-reference write, discarding the only resumable state
- a resume path that re-minted instead of reusing, then attached without checking the target was still unlinked
- missing attach at **five** separate mint sites, each of which would create a second remote issue
- allocation handing back a retired id because a `git log` needed `--full-history`

Roughly half of those were bugs in the *previous wave's fix*. Not one was a judgment failure. This is the class of defect a type checker and a test suite catch in one pass and prose cannot catch at all - which is why the tests written during #241 ended up **grepping markdown for the English word "attach"**.

Run the repo's own "how to spot a mistake" list (CLAUDE.md) against tracker-sync and **zero of the six symptoms fire**. There is no per-item judgment, no code investigation, no ambiguity resolution in issuing `gh issue create --title X --body-file Y`. The host agent is the intelligence, but nothing here needs intelligence.

**The change:** flowctl owns the wire. Skills keep judgment. Prose stops containing `gh api` and starts calling `flowctl tracker comment <id> --body-file X`.

**Who is affected:** tracker-sync users only. The bridge-inactive path - the documented default - performs one config read and loads no adapter reference today, and that is unchanged. There is no downside for the majority of users because there is no new behavior on their path.

**Why it is also faster.** Two compounding wins. Every operation currently costs agent tokens to read adapter prose and reason about which branch applies; those become a subprocess call. And the destination ids that today are re-derived per run get resolved once at discovery (below), removing a round-trip per status write on Jira and per mint on Linear.

## Architecture & Data Models
<!-- scope: technical -->

### The split

| flowctl (deterministic) | skill (judgment) |
|---|---|
| transport ladder: graphql / gh / glab / rest | **MCP rung** - host-agent-visible tools, unreachable from a subprocess |
| create, read, update body/title, comment CRUD | discovery ceremony (interactive, asks the user) |
| status transitions, labels, assignees | 3-way body-merge **conflict adjudication** |
| attachments (upload + retrieve) | what a lifecycle comment should *say* |
| relations / dependency projection | recovery from a structured flowctl error |
| sequencing, ordering, retry, recovery records | |
| receipts, dedup, defer/queue | |

The MCP boundary is real and load-bearing: `linear-mcp.md` states the tool surface is host-agent-visible with **no shell command**. flowctl cannot reach it. The pattern that resolves this already exists in this repo - `create-first-put` records what the agent's `writeIssue` returned. The agent performs the unreachable call; flowctl owns the state atomically. MCP becomes exactly that: agent calls the tool, hands the result to flowctl to persist.

### Destination resolution: resolve once, consume deterministically

`tracker.perTracker` already holds `teamId`, `projectId`, `project`, `host`, `baseUrl`, `projectKey`, `authScheme`, `apiVersion`, `statusMap`. The discovery ceremony already writes them. **That stays agentic** - choosing a project or team is ambiguous, one-time, and needs the user.

What changes is *what* gets resolved. The smoke pass proved that several ids cannot be derived from a name at runtime without an extra API call, and one of them makes a whole feature undecidable:

**New block `tracker.resolved`** - a discovery-written cache, never hand-edited, carrying the fully-resolved destination plus a capability descriptor:

```
tracker.resolved = {
  "resolvedAt": "<iso8601>",
  "destination": { ... per-tracker, below ... },
  "capabilities": {
    "attachments": true|false,
    "blockedBy":   true|false,
    "subIssues":   true|false,
    "deleteIssue": true|false
  }
}
```

Per-tracker `destination` contents, each justified by a measured finding:

| tracker | resolved fields | why it must be pinned |
|---|---|---|
| GitHub | `owner`, `repo` | stable; `subIssues` capability recorded |
| GitLab | `projectId` (**numeric**), `projectPath`, `host`, `plan` | API paths take the id; **the path changes on rename**. `plan` (`free` / `ultimate_trial` / ...) decides dependency degradation |
| Linear | `teamId`, `teamKey`, `stateIds{normalized -> stateId}`, `labelIds` | status writes need a `stateId`, and `type: started` maps to **two** states (In Progress, In Review) - the tiebreak must be decided once, by a human, not guessed per run |
| Jira | `baseUrl`, `projectKey`, `projectId`, `issueTypeId`, `apiVersion: 2`, `style`, `transitions{statusCategory -> transitionId}` | status **cannot** be set via fields (400). It requires a workflow-specific transition id, so without a cache every status write costs a `GET /transitions` first |

The Linear and Jira rows are the speedup. Today a Jira status write is two round-trips (discover transitions, then transition); with the cache it is one. Linear minting likewise stops re-resolving the team and state.

`capabilities` is not decoration - each entry is a measured asymmetry:

- **`attachments: false` on GitHub.** There is no issue-attachment API (`POST /issues/:n/uploads` returns 404). The only route is committing the asset, and on a private repo the raw URL carries an **expiring token**, so it is not a durable link.
- **`blockedBy`** is GitLab tier-gated. Free returns `Blocked issues not available for current license`; Ultimate works. Detectable via `GET /namespaces/:id -> plan`. With the capability recorded, dependency projection degrades to `relates_to` **and says so in the receipt** instead of failing opaquely.
- **`subIssues: true` on GitHub** - `POST /issues/{n}/sub_issues` works (hierarchy, not blocking).
- **`deleteIssue: false` on GitHub** - issues cannot be deleted, only closed `not_planned`.

### Staleness

Workflow states and transition ids change when a human edits the board. The cache is therefore an **optimization, never a source of truth**:

1. Operations use `tracker.resolved` when present.
2. A miss or a rejection that indicates a stale id triggers **resolve-on-miss**: re-derive, retry once, persist the new value.
3. `flowctl tracker resolve --refresh` re-runs resolution explicitly.
4. A stale cache never hard-fails an operation. Degrade and record, consistent with the existing best-effort contract.

### Body fidelity is a per-adapter concern, not a shared one

Measured by posting one identical 391-byte markdown fixture to all four and diffing byte-for-byte:

| tracker | issue body | comment |
|---|---|---|
| Jira (v2) | byte-identical | identical |
| GitHub | byte-identical | identical |
| GitLab | **strips the trailing newline** | same |
| Linear | **rewrites the description** | identical |

Linear's normalization, measured: `_italic_` to `*italic*`, `[l](url)` to `[l](<url>)`, `- bullet` to `* bullet`, `|---|---|` to `| -- | -- |`, `- [x]` to `- [X]`, trailing newline stripped. Comments are untouched.

**Consequence:** a body merge that compares against what we *sent* conflicts on every reconcile against Linear and on every trailing newline against GitLab. The merge base MUST be seeded from the **post-write readback**. flow-next already does this; this spec makes it a tested invariant rather than an incidental behavior, and adds a normalization step so the comparison is stable.

**Jira uses API v2, not v3.** v2 accepts and returns a plain string and Jira auto-converts it to ADF for v3 readers (verified: a markdown bullet list came back as a real ADF `bulletList`). ADF is therefore **not** forced, and the transport can be a uniform string on Cloud and Data Center alike. The current `apiVersion` default of `3` for Cloud should become `2`.

## API Contracts
<!-- scope: technical -->

New flowctl surface, all verb-shaped and destination-aware:

```
flowctl tracker resolve [--refresh] [--json]        # write/refresh tracker.resolved
flowctl tracker create --title T --body-file F [--json]
flowctl tracker read <id> [--json]
flowctl tracker update <id> [--title T] [--body-file F]
flowctl tracker comment <id> --body-file F
flowctl tracker comment-list <id> [--json]
flowctl tracker comment-update <comment-id> --body-file F
flowctl tracker comment-delete <comment-id>
flowctl tracker status <id> --to <normalized-status>
flowctl tracker label <id> [--add L]... [--remove L]...
flowctl tracker attach <id> --file F                # capability-gated
flowctl tracker attach-get <attachment-id> --out F
flowctl tracker relate <id> --blocked-by <other>    # capability-gated, degrades
flowctl tracker list-open [--json]
```

Every command:
- resolves transport from config + env, never re-asks
- returns structured JSON with a stable error shape (`{"success":false,"error":...,"class":...}`) so the skill can adjudicate rather than parse prose
- writes a receipt, exactly as today
- is a no-op returning `class: "inactive"` when the bridge is inactive

## Edge Cases & Constraints
<!-- scope: technical -->

Each of these is a measured behavior, not a hypothetical:

- **No tracker dedups on create.** Identical title+body produced a second issue on GitHub (`#2`), GitLab (`iid 2`) and Linear (`FLOW-64`). The client-side recovery record is the ONLY duplicate defence, and the pre-create window (issue created, process dies before the record is written) stays genuinely open. The contract must state that rather than imply it is closed.
- **`glab` prints its "Multiple config files found" warning to stdout**, corrupting JSON parsing. Hit live during the smoke.
- **`glab api -F file=@` produces invalid multipart** and **`-f "assignee_ids[]="` is not array-encoded**. Both require raw curl.
- **GitLab notes mix system notes with user comments** (`system: true` for "changed title"). Comment sync must filter or it ingests GitLab's own audit trail.
- **GitLab attachments are retrievable only via `GET /projects/:id/uploads/:upload_id`.** The `/uploads/<secret>/file` path in the markdown GitLab returns needs a session cookie; an API token gets 302 then 403 HTML.
- **Jira attachment upload requires `X-Atlassian-Token: no-check`, and omitting it returns 404**, which reads as a wrong endpoint rather than a missing header.
- **GitLab states are `opened`/`closed`**, not `open`/`closed`.
- **GitHub `state_reason` accepts an undocumented `duplicate`**; the docs list only `completed`/`not_planned`/`reopened`.
- **Linear labels must exist before attaching**; GitHub and GitLab create on demand.
- **Linear rate-limits on complexity** (`x-ratelimit-complexity-limit: 3000000`), not request count. GitHub is 5000/hr, Jira 350.
- **Jira Cloud cannot reproduce custom project keys** (`MY_PROJECT`, >10 chars) - Cloud enforces uppercase-alphanumeric, max 10. The display-only path that caused a P1 in #241 stays **unverified** without a Data Center instance and must be specified from existing prose and marked as such.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A `flowctl tracker` command group exists implementing create / read / update / comment CRUD / status / label / list-open against all four adapters, with a stable JSON result shape and a structured error class. Each command writes a receipt exactly as the current skill path does.
- **R2:** `tracker.resolved` is written by the discovery ceremony and carries `destination` + `capabilities` + `resolvedAt`. Contents per tracker are at least the fields in the Architecture table.
- **R3:** Status writes consume the resolved ids. A Jira status change performs **one** request (the transition), not a discover-then-transition pair, when the cache is warm.
- **R4:** Resolve-on-miss: a stale or rejected resolved id triggers one re-resolution and retry, persists the new value, and never hard-fails the operation. `flowctl tracker resolve --refresh` re-runs resolution explicitly.
- **R5:** `capabilities` gates capability-dependent verbs. `attach` on GitHub, and `relate --blocked-by` on GitLab Free, degrade with the degradation named in the receipt rather than erroring opaquely.
- **R6:** GitLab tier is detected via `GET /namespaces/:id -> plan` and recorded. Dependency projection uses `is_blocked_by` on Premium and above, `relates_to` on Free.
- **R7:** Jira uses `apiVersion: 2` for body operations on Cloud and Data Center. A plain-string body round-trips byte-exact; the ADF conversion for v3 readers is Jira's own and is not performed by flow-next.
- **R8:** The merge base is seeded from the **post-write readback**, and body comparison normalizes the measured per-adapter mutations (Linear description rewriting, GitLab trailing-newline stripping). A no-op reconcile against an unmodified issue produces **no** diff on any of the four. This is asserted by test, per adapter.
- **R9:** Comment sync filters GitLab system notes (`system: true`).
- **R10:** Attachments upload AND retrieve byte-identically on Jira, Linear and GitLab, asserted by test with a fake transport. GitHub records `attachments: false` and the commit-and-link workaround documents the expiring-token caveat for private repos.
- **R11:** The adapter reference files shrink to **transport-shape documentation only**. No `gh api` / `glab api` / `curl` invocation remains in skill prose as an instruction to execute. Measured: the tracker-sync prose surface drops by at least 150,000 characters.
- **R12:** The skill retains and documents exactly four judgment surfaces: the MCP rung, the discovery ceremony, conflict adjudication, and comment content synthesis. Each is named in `SKILL.md` with why it cannot be deterministic.
- **R13:** Every behavior in Edge Cases is covered by a test against a fake transport, including the no-dedup reality and the pre-create window being open.
- **R14:** The bridge-inactive path is byte-for-byte unchanged: one config read, no adapter reference loaded, no new output. Asserted by the existing reached-path harness.
- **R15:** Lifecycle touchpoints call `flowctl tracker <verb>` directly. The `tracker-runner` subagent dispatch and the per-skill gating-predicate prose are removed, since a subprocess call needs neither.
- **R16:** The Jira Data Center custom-key path (`MY_PROJECT-7`, >10 chars) is implemented from existing prose and **explicitly marked unverified** in both code comment and spec, with a smoke task gated on a DC instance becoming available.

## Boundaries
<!-- scope: business -->

**In scope:** the four existing adapters; the deterministic verb surface; destination resolution and capability caching; the fidelity/merge-base invariant.

**Out of scope:**
- New tracker types. No fifth adapter.
- Closing the pre-create window. It needs provider idempotency keys (not uniformly offered) or a persisted pre-create intent plus a title search on resume. Named honestly, deferred.
- Replacing the MCP rung. It stays agentic by necessity.
- Changing the projection model or the hybrid id scheme. Both are settled by fn-134 and unaffected.
- Any change to the bridge-inactive default path.

## Decision Context
<!-- scope: both -->

### Why invert now rather than keep hardening prose

#241 is the evidence. Twenty-two waves, every finding deterministic, half of them regressions in the previous fix, and a test suite reduced to grepping English. The subsystem is not badly written prose; it is correctly-written prose doing a job prose cannot do.

### Why the destination cache is part of this and not a follow-up

Because two adapters cannot execute a status write without ids that only an API call yields. Jira **cannot** set status via fields (measured: 400) and needs a workflow-specific transition id. Linear needs a `stateId`, and `type: started` maps to two states, so the choice is genuinely ambiguous and belongs to a human at discovery time, not to a heuristic at runtime. Deterministic execution is not possible without resolved destination state, so it is the same change.

### Why discovery stays agentic

Choosing "which project" is ambiguous, one-time, and interactive - the textbook skill case. The split is not "agentic bad, deterministic good"; it is **discovery is judgment, execution is plumbing**.

### What was verified and what was not

All four adapters were smoke-tested live against real APIs on 2026-07-26: create, read, update, comment CRUD, status, labels, assignees, relations, attachments (upload **and** byte-compared download), list/search, rate limits, and body fidelity via an identical 391-byte fixture. Artifacts were deleted or closed.

Two claims made during that pass were wrong and are corrected here: GitLab `is_blocked_by` is **tier-gated, not unavailable** (the first test ran in a Free personal namespace while the Ultimate trial was group-scoped), and GitHub **does** have a relations API (`sub_issues`).

Not verified: the Jira Data Center custom-key path, which Jira Cloud cannot reproduce.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_tracker_config test_tracker_sync_state test_tracker_sync_gitlab test_tracker_sync_jira -q
```

Full gate once at completion: `python3 scripts/run_tests_parallel.py`
