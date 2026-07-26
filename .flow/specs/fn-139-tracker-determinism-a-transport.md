# Tracker determinism A: transport foundation, distribution, resolved cache

## Goal & Context
<!-- scope: business -->

**This is spec A of a three-spec batch** (A foundation, B verb surface, C teardown). None of them cuts a release alone; the batch releases together.

Tracker-sync is **476,883 characters of prose** describing API calls, containing **112 literal invocations** (`gh api`, `glab api`, `curl -sS`). That is code written in a language that cannot be executed, type-checked, or unit-tested.

The evidence is PR #241: **22 cross-model review waves**, and every bug found was deterministic - an unreachable `else`, a recovery record cleared before the write it protected, a resume path that re-minted instead of reusing, missing attach at five mint sites, an allocator handing back a retired id. Roughly half were regressions in the *previous wave's fix*. Not one was a judgment failure. The tests written during that PR ended up **grepping markdown for the English word "attach"**.

Run CLAUDE.md's "how to spot a mistake" list against tracker transport and **zero of six symptoms fire**. Nothing about `POST /issues` needs intelligence.

**Spec A builds the floor**: how the code ships, how it talks to a network, and how a destination is resolved once instead of per operation. It deliberately contains no user-visible verbs - those are spec B - because A is where the architectural risk lives and it should be reviewed and landed on its own.

**Who is affected:** tracker-sync users only. The bridge-inactive path (the documented default) is unchanged, and that is asserted, not asserted-to-be-obvious.

## Architecture & Data Models
<!-- scope: technical -->

### The distribution constraint comes first

flowctl ships as **named files, not a package**. `install-codex.sh:245-251` copies exactly `flowctl` and `flowctl.py` by name; copy-mode setup writes a fixed list into `.flow/bin/`; Ralph scaffolding does the same. A new package would simply not ship, and installed flowctl would fail on import.

Measured facts that make the split viable anyway:

- The launcher runs `flowctl_bootstrap.py` **as a script**, so `sys.path[0]` is that file's directory. A sibling package is importable in both plugin mode and `.flow/bin` copy mode with no import-machinery change.
- **Cursor ships it free**: `install-cursor.sh:72` is a blanket `rsync -a --delete` with excludes.
- `flowctl.cmd` already exists; the interpreter probe (`py -3` -> `python3` -> `python`) is unaffected by a package.

What must change: `install-codex.sh`, the copy-mode file list, `SOURCE_SHA256` (which today pins exactly **one** file at `flowctl_bootstrap.py:20` and must become a manifest), and every test that loads flowctl via `spec_from_file_location` (there `sys.path[0]` is the *test* directory, so `scripts/` must be on the path - some tests already do this, not all).

**Decision, made and not to be re-litigated mid-implementation:** split the file. The package is **namespaced `flowctl_tracker/`**, never a bare `tracker/`, because it lands on `sys.path` and a generic name invites collisions.

### Injected executor

Adapters never call `subprocess.run` or open a socket directly. They call an **injected request executor**. That seam is the fake transport the whole test strategy in B rests on, so it is defined here rather than retrofitted.

"Typed" means specified, not aspirational:

- **`Request`**: `provider`, `op`, `method`, `url_or_argv`, `headers` (**never authorization**), `body`, `connect_timeout_s`, `read_timeout_s`, `idempotent: bool`.
- **Secrets are injected by the executor, after the adapter boundary.** An adapter never sets an authorization header - if it did, the credential would already have crossed the boundary the redaction rule exists to protect. The executor resolves the provider's credential and attaches it immediately before dispatch.
- **`TrackerError`**: the normalized failure shape every adapter classifier returns - `{class, message, retry_after_s|None, details|None}`. Adapters never raise transport-native exceptions upward.
- **Retry predicate**, explicit: retry iff `class == rate_limited and request.idempotent`. `idempotent` is not decorative.
- **`Response`**: `status`, `headers`, `body`, `elapsed_s`. GraphQL errors arriving over **HTTP 200/400** are normalized here, not in each adapter.
- **Bounds** (defaults, config-overridable): connect **5s**, read **30s** (separate values, not one `timeout_s`); **2** retries max; exponential backoff capped at 30s; concurrency cap 4.
- **Credential precedence**, fixed: explicit env -> Keychain -> CLI config (e.g. `glab`) -> unauthenticated. Redaction happens at the executor boundary so no adapter can leak a token into a log or error.
- **Classification is per-adapter and tabulated**, not a global rule. `401/403 = auth` is insufficient: GitLab returns 403 for *both* a bad token and a licence-gated `is_blocked_by`, so the GitLab table maps 403 **with the licence message body** to `capability` and bare 403 to `auth`. Linear rate limiting arrives as a GraphQL error over HTTP 400, so its table maps that to `rate_limited`.
- **CLI serialization**: every command emits the JSON envelope on **stdout**; human-readable notes go to **stderr**. `--json` is accepted and ignored (always-JSON) so callers need no branch.

### `tracker.resolved`: resolve once, consume deterministically

`tracker.perTracker` already holds `teamId`, `projectId`, `project`, `host`, `baseUrl`, `projectKey`, `authScheme`, `apiVersion`, `statusMap`, written by the discovery ceremony. **Discovery stays agentic** - choosing a project is ambiguous, one-time, and interactive.

What changes is *what* gets resolved, because two adapters cannot execute a status write without ids only an API call yields:

```
tracker.resolved = {
  "resolvedAt": "<iso8601>",            // "all required fields complete" - NOT a TTL input
  "destinationResolvedAt": "<iso8601>",
  "capabilitiesCheckedAt": "<iso8601>",
  "destination": { ...per-tracker... },
  "capabilities": { "attachments": bool, "blockedBy": bool, "subIssues": bool, "deleteIssue": bool }
}
```

| tracker | resolved fields | why it must be pinned |
|---|---|---|
| GitHub | `owner`, `repo` | stable |
| GitLab | **numeric** `projectId`, `projectPath`, `host`, `namespaceId`, `plan` | API paths take the id and **the path changes on rename**; `plan` decides dependency degradation |
| Linear | `teamId`, `teamKey`, `stateIds{normalized -> stateId}`, `labelIds` | status writes need a `stateId`, and `type: started` maps to **two** states (In Progress, In Review) - a human decides that tiebreak once, at discovery |
| Jira | `baseUrl`, `projectKey`, `projectId`, `issueTypeId`, `apiVersion: 2`, `style`, `statusIds{normalized -> statusId}` | status **cannot** be set via fields (measured: 400). **Transition ids are NOT cached**: `jira.md:738` states they are valid only FROM the current status, verified live (To Do -> In Progress -> Done each surfaced different ids). Only the stable target **status** ids are pinned |

**Capability truth table, decided here so B cannot leave it open:**

| | attachments | blockedBy | subIssues | deleteIssue |
|---|---|---|---|---|
| GitHub | **false** (no API; 404) | false (no issue-level blocked-by) | **true** (`sub_issues`) | **false** (close `not_planned` only) |
| GitLab | true (via `uploads/:upload_id`) | **plan-dependent**: `free` -> false, Premium+ -> true | false | true |
| Linear | true (presigned two-step) | true | false | true |
| Jira | true (needs `X-Atlassian-Token: no-check`) | true (`Blocks`, works on free tier) | false | true |

`subIssues` and `deleteIssue` are **kept**, with consumers assigned in B (dependency projection may use GitHub sub-issues as its degraded form; `deleteIssue` gates cleanup paths). They are not "may be dropped".

GitLab's tier probe needs a **namespace id**, which is why `namespaceId` is pinned alongside `projectId` - without it the TTL re-probe costs an extra lookup to rediscover it.

A **failed TTL re-probe is not a capability change.** It is reported in a separate `probe` field `{scope, at, ok, reason}`, distinct from `degraded`, which means an actual capability transition.

Linear stops re-resolving team and state on every mint. **Jira does not get faster**: a status write must still `GET .../transitions` for the issue's current status before transitioning, because transition ids are current-state-relative. An earlier draft of this batch claimed the cache made it one request; that was wrong and is corrected here. The Jira win is correctness (the right status id, pinned once), not latency.

### Cache state transitions

One explicit table, not prose rules that contradict each other:

| state | trigger | action | human? |
|---|---|---|---|
| absent block | post-upgrade first run | explicit one-time backfill; capability-gated callers get `class: unresolved`, never a false `false` | no |
| absent field | partial prior resolution | scoped re-resolve of that field only | no |
| stale value | write rejected `stale_id` **(spec B)** | attempt 1: scoped re-resolve + retry. attempt 2: same once more. Both failed -> retry exhausted | no |
| capability downgrade | write rejected `capability` **(spec B)** | degrade, structured `degraded` field, existing relations left intact | no |
| capability upgrade | **`capabilitiesCheckedAt`** older than `capabilityTtlHours` (default 24), checked on any consuming call - a scoped destination refresh must NOT make capabilities look fresh | **synchronous, bounded** re-probe (one request, own timeout). No background process: no daemon, no lifecycle, and a failed probe leaves the prior capability and reports it | no |
| ambiguous Linear state | cached `stateId` gone AND >1 live state shares its `type` | `class: conflict`, surface both candidates | **yes** |
| auth failure | 401/403 | `class: auth`, no retry, **no degradation** - never misread as a tier downgrade | yes |
| retry exhausted | both attempts failed **(spec B)** | `class: unresolved`, operation fails cleanly, cache untouched | yes |

**Rows marked (spec B) are triggered by a mutation verb, which spec A does not expose.** A defines and unit-tests the state machine and its transitions through a seam; B wires the real verbs into it and tests them end to end. A's own `resolve` covers the absent-block, absent-field, ambiguous-state and auth rows.

The GitLab tier probe specifically must not read a transient 403 as a downgrade: only a `capability`-classed rejection from an actual write flips a capability.

## API Contracts
<!-- scope: technical -->

Spec A ships resolution only. The verb surface is spec B.

```
flowctl tracker resolve [--refresh] [--scope <path>]

Scopes are **exact nested paths**, each with its own timestamp: `destination`, `destination.statusIds` (Jira), `destination.stateIds` (Linear), `capabilities`.
flowctl tracker resolve --select <normalized>=<stateId>    # persists a human tiebreak, validated against live candidates
```

**Result envelope** (established here, consumed by B):

```
{"success": true,  "data": {...}, "degraded": null | {"capability","from","to","reason"}, "probe": null | {"scope","at","ok","reason"}}
{"success": false, "class": "<enum>", "error": "<human string>", "retryable": bool, "details": null | <typed variant>}

`details` is a **typed variant keyed by class**, not free-form: `conflict` carries `{candidates: [{id,name,type}]}` so an ambiguous Linear state surfaces both options structurally; `rate_limited` carries `{retry_after_s}`; `capability` carries `{capability, required_plan}`. Every variant's exact serialization is asserted.
```

`class` enum, fixed and exhaustive: `inactive`, `unresolved`, `stale_id`, `auth`, `rate_limited`, `transport`, `not_found`, `capability`, `conflict`, `invalid_input`. Exit codes fixed and numeric: `0` success, `2` invalid_input, `3` inactive, `4` unresolved, `5` auth, `6` rate_limited, `7` transport, `8` not_found, `9` capability, `10` conflict, `11` stale_id.

**Degradation is a structured field, never a sentence in a receipt note.**

## Edge Cases & Constraints
<!-- scope: technical -->

Measured live on 2026-07-26 against all four real APIs:

- **No tracker dedups on create.** Identical title+body produced a second issue on GitHub (`#2`), GitLab (`iid 2`) and Linear (`FLOW-64`). Client-side recovery is the ONLY duplicate defence; the pre-create window stays genuinely open and is stated, not implied closed.
- **GitLab tier is group-scoped.** A personal-namespace project stays Free during a group trial. Detect via `GET /namespaces/:id -> plan` (`free` | `ultimate_trial` | ...). Verified both ways: Free rejects `is_blocked_by`, Ultimate accepts it.
- **`glab` prints its "Multiple config files found" warning to STDOUT**, corrupting JSON parsing.
- **`glab api -F file=@` produces invalid multipart** and **`-f "assignee_ids[]="` is not array-encoded**; both need raw curl.
- **Jira status cannot be set via fields** (400) and needs a transition id.
- **Jira v2 accepts and returns a plain string**; Jira converts to ADF for v3 readers itself. ADF is not forced.
- Rate limits differ in kind: Linear is **complexity**-based (`x-ratelimit-complexity-*`), GitHub 5000/hr, Jira 350.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The adapter package ships on **every** runtime: plugin mode, copy-mode `.flow/bin`, `install-codex.sh`, `install-cursor.sh` **and `install-cursor.ps1`**, and Ralph scaffolding. A CI packaging smoke imports the package on each runtime row including Windows.
- **R2:** Integrity is verified **by the installers, and nowhere else** - one design, chosen because the alternatives are not executable. `flowctl_bootstrap.py` runs only for a bare `usage` / `--help` (`flowctl:44-48`); ordinary commands exec `flowctl.py` directly, so there is no existing runtime verification point. The rejected alternatives, and why: **per-command hashing** taxes every invocation of a very hot CLI; a **persisted verification marker** needs a digest-keyed invalidation lifecycle that is itself a source of staleness bugs. So: each controlled installer verifies the manifest after copying and **fails loudly**, the manifest enumerates its members explicitly, and a CI packaging smoke covers every runtime.
  **Stated residual gap:** a marketplace/plugin install has no plan-controlled post-install hook, so a corrupt package there is **not** detected by flow-next - it surfaces as an ordinary Python `ImportError` on first use. That is a real hole, accepted deliberately rather than papered over with machinery that would not reliably fire.
- **R3:** Every test that loads flowctl via `spec_from_file_location` has `scripts/` on `sys.path`, so the package imports under test as it does in production.
- **R4:** Adapters call an **injected request executor**; no adapter calls `subprocess.run` or opens a connection directly. The executor is substitutable, and that substitution is the fake transport spec B tests against.
- **R5:** No shell. Content-bearing arguments (bodies, comments, titles) travel via stdin or a file, never argv - the existing flowctl prompt-injection lesson applies directly to issue bodies.
- **R6:** Credentials are read per run from env/Keychain, **never persisted** into `tracker.resolved`, never logged, never included in a receipt or error string.
- **R7:** Every request has an explicit timeout; retries are bounded and apply to `rate_limited` only, with backoff read from each adapter's own header shape; concurrency is capped. TLS verification defaults on, with the existing per-tracker `sslVerify` opt-out staying explicit.
- **R8:** The resolve transaction is specified precisely, because atomic-write plus a lock prevents clobbering but **not stale resolution**: a resolver can query project A, then a `config set` repoints the tracker to project B, and the resolver merges A's ids into B's config. Required: **fingerprint every discovery input** used for the network work (tracker type, project/team identity, host, baseUrl) and compare it **inside the lock**; on mismatch discard and boundedly re-resolve, or return `class: conflict`. Order: network work **outside** the lock; acquire the lock; re-read; compare fingerprint; merge **only the resolved scope**; validate; atomically replace.
- **R8b:** The lock is a **specified cross-platform primitive**, not "the existing one": its path, acquisition timeout, stale-owner recovery and crash behavior are defined, and **every `.flow/config.json` writer routes through it** - today `set_config` and `cmd_init` both write without it and can race a resolve. Contention and crash-recovery are exercised on the **Windows CI row**, not only POSIX.
- **R9:** `flowctl tracker resolve` **explicitly backfills** an absent block for all four adapters, populating `destination` + `capabilities` per the Architecture table. This is distinct from a *consuming verb* meeting an absent block, which returns `class: unresolved` rather than resolving implicitly mid-operation - the two behaviors are separately specified and separately tested.
- **R10:** Every row of the cache state table is implemented and tested, including that an absent block yields `class: unresolved` and **not** a false capability `false`, and that a transient 403 on the tier probe does not flip a capability.
- **R11:** `resolve --select` persists a human's Linear tiebreak, validated against live candidates. `resolvedAt` is stamped only once all required fields are present.
- **R12:** `--scope` re-resolves only the named nested path and stamps only that path's timestamp. Note the scope set contains **no transitions**: Jira transition ids are never cached (they are valid only from the current status), so transition rejection and re-fetch are spec B's concern, not a cache scope here. A resolves stable `statusIds` only.
- **R13:** Existing persisted `perTracker.apiVersion: 3` configs are **migrated to 2**, not orphaned.
- **R14:** The result envelope, `class` enum and numeric exit codes are implemented and asserted, so callers branch on structure rather than parsing prose.
- **R15:** The **bridge-inactive path is byte-for-byte unchanged**: one config read, no adapter import, no new output. Asserted by the existing reached-path harness.

## Boundaries
<!-- scope: business -->

**In scope:** distribution, the executor seam, destination + capability resolution, the cache state machine, the result/error contract.

**Out of scope:**
- Every user-facing verb (create, read, update, comment, status, label, attach, relate). Spec **B**.
- All prose teardown, doc updates and baseline re-freezing. Spec **C**.
- Closing the pre-create window - needs provider idempotency keys nobody uniformly offers.
- Batching. It becomes *possible* once transport is code, but has no API or acceptance criterion here and is not a benefit this batch delivers.
- Any change to body-merge conflict adjudication, which stays agentic (see Decision Context).

## Decision Context
<!-- scope: both -->

### Why split the file rather than grow flowctl.py

`flowctl.py` is already 32,919 lines. But the deciding factor was not taste - it was checking whether a package can actually ship. It can: the launcher execs the bootstrap as a script so `sys.path[0]` is its directory, Cursor's installer is a blanket rsync, and `flowctl.cmd` already handles Windows. The cost is bounded and enumerated (R1-R3). The alternative - adapters inside a 33k-line file - was rejected as the more expensive long-term option, not the cheaper one.

### The strongest counter-evidence, and why it does not apply

Memory `plan-sync-skip-gate-not-viable-2026-07-03` records a deterministic gate that was built, evaluated, and **killed by its own eval**: a false skip with zero path signal, and the conclusion that "any deterministic proxy is either unsafe or so conservative it never skips."

That is the right warning to hold here, and it is why **body-merge conflict adjudication stays agentic** across this whole batch. Body reconciliation is more semantic than plan-sync drift detection, not less. What moves is transport: `POST /issues` with a title and a body. If any task in this batch ever proposes making conflict resolution deterministic, it is out of scope by construction.

### fn-57 R3 is superseded

fn-57's R3 states "flowctl gains **no tracker-mutation code** - all status / comment / link mutations stay agent-driven". This batch reverses it deliberately. Spec **C** updates the three places that assert the old rule (`cmd_sync_check`'s docstring, the `list-dep-relations` docstring, `docs/tracker-sync.md`'s "flowctl has no tracker transport" line) so nothing ships contradicting a live criterion.

### What was verified and what was not

All four adapters were smoke-tested live on 2026-07-26: create, read, update, comment CRUD, status, labels, assignees, relations, attachments (upload **and** byte-compared download), search, rate limits, and body fidelity via an identical 391-byte markdown fixture. Every artifact was deleted or closed.

Two claims made during that pass were wrong and are corrected here: GitLab `is_blocked_by` is **tier-gated, not unavailable** (the first test ran in a Free personal namespace while the trial was group-scoped), and GitHub **does** have a relations API (`sub_issues`).

Not verified: the Jira Data Center custom-key path, which Jira Cloud cannot reproduce (Cloud enforces uppercase-alphanumeric keys, max 10 chars). It is implemented from prose in spec B and marked unverified.

## Observability

Long synchronous waits (a bounded re-probe, a retry with backoff) must not look like a hang. Every attempt, backoff, scope and probe failure emits a **redacted event on stderr**, while stdout stays exactly one JSON envelope so callers parse without branching.

## Quick commands

New focused modules this spec adds, each named so the work has a completion oracle:

```bash
cd plugins/flow-next/tests && python3 -m unittest \
  test_tracker_executor test_tracker_classify test_tracker_resolved_cache \
  test_tracker_resolve_github_gitlab test_tracker_resolve_linear_jira \
  test_tracker_distribution test_tracker_config test_startup_bootstrap -q
```

**Provider fixture matrix** (required, not optional): for each of the four providers, recorded response shapes for success, `auth`, `rate_limited` (with that provider's own header/GraphQL shape), `not_found`, `capability`, and a malformed body - so the classifier tables are asserted against real shapes rather than invented ones.

Full gate once at completion: `python3 scripts/run_tests_parallel.py`
