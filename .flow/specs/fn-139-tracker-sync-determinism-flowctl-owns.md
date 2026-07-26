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

**Why it is also faster**, in rough order of magnitude:

1. **Context.** A tracker-sync run today reads `steps.md` (86k chars) plus the relevant adapter reference (40k-75k) - roughly **120,000-160,000 characters, 30-40k tokens, per run**. A `flowctl tracker <verb>` call loads none of it.
2. **Inference.** Every operation currently costs at least one model turn to walk the transport ladder, pick a branch and construct the call. A subprocess call infers nothing; wall-clock goes from seconds to about a hundred milliseconds.
3. **Dispatch.** The `tracker-runner` subagent exists because a lifecycle comment needed an agent. A subprocess does not, so the whole background-dispatch path and its per-skill gating prose disappear (R15).
4. **Batching.** Deterministic code can batch and parallelize adapter calls. Prose cannot; today every operation is strictly serial.
5. **Round-trips.** Destination ids re-derived per run get resolved once at discovery (below), removing a request per status write on Jira and per mint on Linear.

The last one is the smallest. The first is the one users will feel.

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

### Identifier semantics (every verb states which it takes)

Three id kinds exist and were previously conflated:

| kind | example | used by |
|---|---|---|
| **spec id** | `fn-1-slug`, `wor-17-slug` | spec-aware verbs (anything writing local state or a receipt) |
| **durable tracker id** | GitHub `node_id`, GitLab global `id`, Linear UUID, Jira issue id | the dedupe key stored in `tracker.id` |
| **display identifier** | `#1`, `group/project#12`, `FLOW-63`, `SCRUM-1` | human-facing, and the ONLY thing Linear MCP returns |

Verbs are split into two groups, because conflating them is what made the receipt contract incoherent:

**Wire verbs** - take a durable tracker id, touch no local state, write no receipt:

```
flowctl tracker wire read <tracker-id>
flowctl tracker wire update <tracker-id> [--title T] [--body-file F]
flowctl tracker wire comment-add <tracker-id> --body-file F
flowctl tracker wire comment-list <tracker-id>
flowctl tracker wire comment-update <tracker-id> <comment-id> --body-file F   # parent id required: GitLab + Jira need both
flowctl tracker wire comment-delete <tracker-id> <comment-id>
flowctl tracker wire label <tracker-id> [--add L]... [--remove L]...
flowctl tracker wire assign <tracker-id> [--add U]... [--remove U]...
flowctl tracker wire attach <tracker-id> --file F
flowctl tracker wire attach-get <attachment-id> --out F
flowctl tracker wire list-open
```

**Spec-aware verbs** - take a spec id, write local state and an event-tagged receipt:

```
flowctl tracker resolve [--refresh] [--scope destination|capabilities|transitions|states]
flowctl tracker create <spec-id> --title T --body-file F [--event E]
flowctl tracker status <spec-id> --to <normalized> [--event E]      # embeds the fn-66 evidence gate
flowctl tracker relate <spec-id> --blocked-by <other-spec-id>       # resolves both ends locally
flowctl tracker sync-body <spec-id>                                 # write + readback + paired merge-base, one transaction
flowctl tracker persist-external <spec-id> --identifier I [--id D] [--url U] --source mcp
```

`persist-external` is the R18 verb. It is spec-aware because it must write `tracker.id` and a receipt.

### Result envelope

Every command emits one JSON object. Success:

```
{"success": true, "data": {...}, "degraded": null | {"capability": "...", "from": "...", "to": "...", "reason": "..."}}
```

Failure:

```
{"success": false, "class": "<enum>", "error": "<human string>", "retryable": true|false}
```

`class` enum, fixed and exhaustive: `inactive`, `unresolved`, `stale_id`, `auth`, `rate_limited`, `transport`, `not_found`, `capability`, `conflict`, `invalid_input`. Exit code maps 1:1 to class so callers branch without parsing prose. **Degradation is a structured field, never a sentence in the receipt note.**

### Receipt ownership

Wire verbs write **no** receipt (they have no spec id, and `sync receipt` requires one - this is the existing constraint that made "every command writes a receipt" incoherent). Spec-aware verbs write one, event-tagged, exactly as today. `create` keeps fn-134's pre-spec **recovery record** path rather than a receipt, because at create time no local spec exists yet.

## Non-functional requirements
<!-- scope: technical -->

- **Module boundary.** Adapters do NOT land in `flowctl.py` (already 32,919 lines). A new `plugins/flow-next/scripts/tracker/` package holds one module per adapter plus a shared typed transport/result layer. `flowctl.py` gains only argparse wiring and dispatch.
- **Injected executor.** Adapters call an injected request executor, not `subprocess.run` directly. That seam IS the fake-transport used by tests, defined in task .1 rather than retrofitted in .6.
- **Subprocess safety.** No shell. Content-bearing arguments (bodies, comments, titles) go via stdin or a file, never argv - the existing `flowctl.py` prompt-injection lesson applies directly to issue bodies.
- **Secrets.** Credentials are read from env/Keychain per run, never persisted into `tracker.resolved`, never logged, never included in a receipt or error string.
- **Bounded everything.** Explicit timeout per request, bounded retry with backoff on `rate_limited` only, and a concurrency cap. Linear's limit is complexity-based (`x-ratelimit-complexity-*`), GitHub 5000/hr, Jira 350 - the adapter reads its own headers.
- **TLS.** Verification on by default; the existing `sslVerify` opt-out stays explicit and per-tracker.
- **Batching is OUT of scope for this spec.** It was cited as a speed benefit with no API and no acceptance criterion. Removed rather than left as an unfalsifiable claim; it can be a follow-up once the verb surface is stable.

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
- **R4:** Cache state transitions are a **single explicit table**, not four prose rules that contradict each other. Every row states trigger, action, retry budget, and whether a human is involved:

  | state | trigger | action | human? |
  |---|---|---|---|
  | absent block | post-upgrade first run | explicit one-time backfill via `tracker resolve`; capability-gated verbs return `class: unresolved`, never a false `false` | no |
  | absent field | partial prior resolution | scoped re-resolve of that field only (`--scope`) | no |
  | stale value | write rejected with a stale-id class | one scoped re-resolve + one retry, then persist | no |
  | capability downgrade | write rejected `capability` (e.g. trial expired) | degrade, emit structured `degraded` field, leave existing relations intact | no |
  | capability upgrade | `resolvedAt` older than `capabilityTtlHours` (default 24) checked on any spec-aware verb | background re-probe; no user-visible stall | no |
  | ambiguous Linear state | cached `stateId` gone AND >1 live state shares its `type` | `class: conflict`, surface both candidates | **yes** |
  | auth failure | 401/403 | `class: auth`, no retry, no degradation (do not misread as a tier downgrade) | yes |
  | retry exhausted | 2 scoped re-resolves failed | `class: unresolved`, operation fails cleanly, cache untouched | yes |

  The GitLab tier probe specifically must not read a transient 403 as a downgrade: only a `capability`-classed rejection from a write flips a capability.

- **R5:** `capabilities` gates capability-dependent verbs. `attach` on GitHub, and `relate --blocked-by` on GitLab Free, degrade with the degradation named in the receipt rather than erroring opaquely.
- **R6:** GitLab tier is detected via `GET /namespaces/:id -> plan` and recorded. Dependency projection uses `is_blocked_by` on Premium and above, `relates_to` on Free.
- **R7:** Jira uses `apiVersion: 2` for body operations on Cloud and Data Center. A plain-string body round-trips byte-exact; the ADF conversion for v3 readers is Jira's own and is not performed by flow-next.
- **R8:** **Server readback is canonical.** The merge base is seeded from what the tracker returns after a write, never from what we sent. Client-side normalization is limited to a short, explicitly-enumerated set of stable transformations (trailing-newline stripping) and does NOT attempt to predict Linear's markdown rewriting - that is unsafe around code fences and escapes, and readback already supplies the authoritative body. `tracker sync-body <spec-id>` performs write + readback + paired merge-base as **one transaction**; a partial failure leaves the prior merge base untouched, asserted by test.
- **R9:** Comment sync filters GitLab system notes (`system: true`).
- **R10:** Attachments upload AND retrieve byte-identically on Jira, Linear and GitLab, asserted by test with a fake transport. GitHub records `attachments: false` and the commit-and-link workaround documents the expiring-token caveat for private repos.
- **R11:** The adapter references shrink to transport-shape documentation. Measured **mechanically**, not by eye: a test asserts zero matches for an executable-invocation pattern (`gh api`, `glab api`, `curl -sS`, `POST /rest/api`) inside bash fences across an enumerated file set, and asserts the summed character count of that file set is at least 150,000 below the pre-change baseline recorded in the test itself.
- **R12:** The skill retains and documents exactly **five** judgment surfaces, each named in `SKILL.md` with why it cannot be deterministic: the MCP rung, the discovery ceremony, 3-way body-merge conflict adjudication, comment content synthesis, and **recovery routing from a structured flowctl error**. The earlier "exactly four" was wrong - the architecture table already listed recovery as agentic. Status-sync's deadlock fallback and unmapped-state handling are explicitly assigned: deterministic outcomes are enumerated in the who-wins ladder, and anything left genuinely ambiguous routes to the recovery surface rather than being silently defaulted.
- **R13:** Every behavior in Edge Cases is covered by a test against a fake transport, including the no-dedup reality and the pre-create window being open.
- **R14:** The bridge-inactive path is byte-for-byte unchanged: one config read, no adapter reference loaded, no new output. Asserted by the existing reached-path harness.
- **R15:** Lifecycle touchpoints call `flowctl tracker <verb>` directly. The `tracker-runner` subagent dispatch and the per-skill gating-predicate prose are removed, since a subprocess call needs neither.
- **R16:** The Jira Data Center custom-key path (`MY_PROJECT-7`, >10 chars) is implemented from existing prose and marked unverified in code comment and spec. A **deferred smoke task exists** (task .11) carrying its prerequisite (a reachable DC/Server instance - Jira Cloud enforces uppercase-alphanumeric max-10 keys and CANNOT reproduce it) and its oracle (mint from `MY_PROJECT-7` succeeds display-only, links, and never loops on a rejected mint). It stays `todo` and blocks nothing.
- **R17:** fn-57's **R3 is explicitly superseded.** That criterion states "flowctl gains no tracker-mutation code - all status / comment / link mutations stay agent-driven". fn-139 reverses it deliberately. The reversal is recorded in this spec, and the three in-code assertions of the old rule are updated rather than left contradicting the shipped behavior: `flowctl.py` `cmd_sync_check` (the "NO tracker-mutation code lives here or anywhere in flowctl (R3)" docstring), the `list-dep-relations` transport-blind docstring, and `docs/tracker-sync.md`'s "flowctl has no tracker transport" line.
- **R18:** `flowctl tracker persist-external <spec-id>` records a write the agent performed on a rung flowctl cannot reach (the MCP rung). **Linear MCP returns the display identifier only, never the durable UUID** (`linear-mcp.md:100`), so the verb accepts an identifier-only call and then resolves the UUID via the GraphQL rung before persisting. If GraphQL is unavailable, it persists an **identifier-only linked state**, marks it as such, and a later reconcile completes it - it never fabricates or omits `tracker.id` silently. This closes a window **worse than pre-create**: there nothing was created; here the remote issue exists and without this verb nothing records it. On persist failure the run surfaces identifier + url and writes a warning receipt for manual reconciliation.
- **R19:** `tracker.resolved` writes are **atomic and lock-protected**, reusing the existing `atomic_write_json` and `cross_process_lock` primitives in flowctl.py. Two workers resolving concurrently must not produce a torn or clobbered cache. A partially-resolved block is never persisted with a `resolvedAt` stamp that would make it look warm.
- **R24:** `flowctl tracker status` **embeds fn-66's merge-evidence gate** rather than forwarding the caller's requested status: terminal `Done` only on a GitHub-confirmed MERGED, `In Review` on an open PR, never terminal from completion-review alone.
- **R25:** `flowctl tracker relate` reproduces **fn-64's full contract**, not just the verb shape: the `depRelations` provenance ledger, additive-only writes, the completed-blocker rule, never-clobber-on-collision (defer + queue), and the `<!-- flow:deps -->` fenced block's exclusion from body-merge divergence hashing.
- **R26:** The **paired merge-base snapshot invariant** is preserved: both halves written at one sync point, atomically, never per-flag. This is pre-existing hard-won behavior (memory: `paired-snapshot-setter-must-write-both`) and a deterministic rewrite is exactly where it could regress silently.
- **R27:** The status **who-wins ladder keeps collision cases first**. Its branch order carries correctness dependencies (memory: `who-wins-ladder-must-check-the-...`); a port that reorders them lets an earlier rule win silently.
- **R28:** fn-130's reached-path B1 baselines are re-frozen for the tracker cluster. The task **enumerates every affected fixture** under `optimization/reached-path/fixtures/b1/tracker` rather than "the tracker ones", and records a before/after delta artifact in the same honest form fn-134 used when its own change grew the path.
- **R29:** fn-89's teardown is **clean**: removing the `tracker-runner` agent and its dispatch reference leaves no dangling reference from any of the fourteen calling skills, the codex mirror, or `docs/platforms.md`'s Tier-B dispatch text.
- **R30:** Existing persisted `perTracker.apiVersion: 3` configs are **migrated, not orphaned**, when R7 flips the Jira body default to v2.

- **R31:** Every behavior claimed deterministic has a **reachable verb**. Assignees get `wire assign`; GitHub's undocumented `duplicate` state reason is reachable through `status --reason`; `capabilities.deleteIssue` either gets a verb or is dropped from the descriptor; and Linear's create-label-before-attach rule has defined unknown-label semantics (auto-create vs `class: not_found`, chosen explicitly). No R13 test may target behavior the public surface cannot invoke.
- **R32:** The **injected request executor and adapter interface are defined in task .1**, not retrofitted. Focused regression tests live in the task that writes the code (.1-.5); task .6 is the cross-adapter **conformance matrix plus fault injection** only - open pre-create window, post-write readback, scoped invalidation, lock race, retry exhaustion, rate-limit backoff.
- **R33:** Adapters live in a new `plugins/flow-next/scripts/tracker/` package, one module per adapter over a shared typed transport/result layer; `flowctl.py` gains only argparse wiring. The non-functional invariants above (no shell, content via stdin/file, secrets never persisted or logged, bounded timeout/retry/concurrency, TLS default-on) are asserted by test where testable and by code review where not.

## Boundaries
<!-- scope: business -->

**In scope:** the four existing adapters; the deterministic verb surface; destination resolution and capability caching; the fidelity/merge-base invariant.

**Out of scope:**
- New tracker types. No fifth adapter.
- Closing the pre-create window. It needs provider idempotency keys (not uniformly offered) or a persisted pre-create intent plus a title search on resume. Named honestly, deferred.
- Replacing the MCP rung. It stays agentic by necessity.
- Changing the projection model or the hybrid id scheme. Both are settled by fn-134 and unaffected.
- Any change to the bridge-inactive default path.
- **A fallback to the prose path.** R11/R15 remove it, so flowctl becomes the sole route. This is an accepted consequence, not an oversight: two paths would mean two behaviours to keep in sync, which is the problem being solved. The mitigation is the fake-transport test suite (R13), not a hidden second implementation.

## Decision Context
<!-- scope: both -->

### Why invert now rather than keep hardening prose

#241 is the evidence. Twenty-two waves, every finding deterministic, half of them regressions in the previous fix, and a test suite reduced to grepping English. The subsystem is not badly written prose; it is correctly-written prose doing a job prose cannot do.

### Why the destination cache is part of this and not a follow-up

Because two adapters cannot execute a status write without ids that only an API call yields. Jira **cannot** set status via fields (measured: 400) and needs a workflow-specific transition id. Linear needs a `stateId`, and `type: started` maps to two states, so the choice is genuinely ambiguous and belongs to a human at discovery time, not to a heuristic at runtime. Deterministic execution is not possible without resolved destination state, so it is the same change.

### Why discovery stays agentic

Choosing "which project" is ambiguous, one-time, and interactive - the textbook skill case. The split is not "agentic bad, deterministic good"; it is **discovery is judgment, execution is plumbing**.

### The strongest counter-evidence, and why it does not apply

Memory entry `plan-sync-skip-gate-not-viable-2026-07-03` records a deterministic gate that was **built, evaluated, and killed by its own eval**: a 27-scenario cross-repo run with frozen ground truth produced a genuine false skip, and the conclusion was that "whether a completed task invalidates a downstream plan is a *semantic* question... any deterministic proxy is either unsafe or so conservative it never skips."

That is the right warning to hold against this spec, and it is the reason **body-merge conflict adjudication stays agentic here** (R12). Body reconciliation is more semantic than plan-sync drift detection, not less. What fn-139 moves is not judgment: it is `POST /issues` with a title and a body. The test for whether a candidate belongs in flowctl is the CLAUDE.md symptom list, and for transport it fires zero of six.

If this spec ever grows a task that makes conflict resolution deterministic, that task is out of scope by construction.

### What was verified and what was not

All four adapters were smoke-tested live against real APIs on 2026-07-26: create, read, update, comment CRUD, status, labels, assignees, relations, attachments (upload **and** byte-compared download), list/search, rate limits, and body fidelity via an identical 391-byte fixture. Artifacts were deleted or closed.

Two claims made during that pass were wrong and are corrected here: GitLab `is_blocked_by` is **tier-gated, not unavailable** (the first test ran in a Free personal namespace while the Ultimate trial was group-scoped), and GitHub **does** have a relations API (`sub_issues`).

Not verified: the Jira Data Center custom-key path, which Jira Cloud cannot reproduce.

## Downstream impact

Specs that take a dependency on this one (edges set via `flowctl spec add-dep`):

- **[[fn-138-published-json-schema-for-flow-config]]** - must publish the `tracker.resolved` block; publishing before this lands ships a schema that immediately drifts and fails its own honesty test.
- **[[fn-73-glab-git-ops-make-prresolve-prland-over]]** - reuses the `glab` transport plumbing (token/host resolution, tier probe, structured errors) plus the two measured `glab` defects, rather than deriving a second divergent implementation.

Cross-referenced without a dependency edge:

- **[[fn-129-skill-only-invocation-architecture]]** - **file conflict, not an ordering requirement.** Both edit `flow-next-tracker-sync/steps.md`, `SKILL.md` and `references/*.md`. Scheduling choice; second one in should rebase.

Superseded by this spec:

- **fn-57 R3** ("flowctl gains no tracker-mutation code") - reversed deliberately, see R17.
- **fn-130** tracker-cluster reached-path B1 baselines - invalidated by R11's prose reduction, re-frozen under R28.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_tracker_config test_tracker_sync_state test_tracker_sync_gitlab test_tracker_sync_jira -q
```

Full gate once at completion: `python3 scripts/run_tests_parallel.py`
