# Tracker determinism B: verb surface, capabilities, body fidelity

## Goal & Context
<!-- scope: business -->

**Spec B of a three-spec batch** (A foundation, B verb surface, C teardown). Depends on **fn-139**. None of them cuts a release alone; the batch releases together.

Spec A built the floor: the shipped package, the injected executor, the resolved destination cache, and the result envelope. **B is where prose stops being the implementation.** Every operation the tracker-sync skill currently describes in English - create, read, update, comment, status, label, assign, attach, relate - becomes a flowctl verb backed by tests.

The skill still exists after B. It keeps the five things that genuinely need judgment (spec C names them). What it loses is the 112 literal `gh api` / `glab api` / `curl` invocations it currently asks a language model to compose by hand.

## Architecture & Data Models
<!-- scope: technical -->

### Two verb groups, because conflating them broke the receipt contract

A durable id **cannot address GitHub or GitLab endpoints**: GitHub REST needs the issue `number` while the durable key is the `node_id` (`github.md:207` says explicitly "Never the `number`"), and GitLab needs the project-local `iid` while the durable key is the global `id`. So wire verbs take a **locator**, not an id:

```
--locator '{"durable": "<id>", "display": "<#N | group/project#iid | FLOW-63 | SCRUM-1>"}'
```

The adapter uses whichever field its endpoint needs.

**Validation happens BEFORE the mutation, not after.** Response-only checking is too late: a stale display address would already have updated or commented on the wrong issue by the time the mismatch surfaced, and several providers' comment responses carry only the comment id, not the parent's durable id. So every **write** verb performs a **pre-mutation parent read** that resolves the display address and compares it to `locator.durable`, and **aborts with `class: conflict` on mismatch**. Response validation stays as a second, cheaper check. Read-only verbs may validate on response alone.

The cost is one extra read per write. That is the price of not writing to the wrong issue after a project move or repoint, and it is accepted deliberately.

This costs callers nothing: `sync set-tracker-id <spec> <uuid> --identifier X --url Y` means every linked spec already stores both fields.

**Wire verbs** - take a locator, touch no local state, write no receipt:

```
flowctl tracker wire read           --locator L
flowctl tracker wire update         --locator L [--title T] [--body-file F]
flowctl tracker wire comment-add    --locator L --body-file F
flowctl tracker wire comment-list   --locator L
flowctl tracker wire comment-update --locator L <comment-id> --body-file F
flowctl tracker wire comment-delete --locator L <comment-id>
flowctl tracker wire label          --locator L [--add X]... [--remove X]...
flowctl tracker wire assign         --locator L [--add U]... [--remove U]...
flowctl tracker wire attach         --locator L --file F
flowctl tracker wire attach-get     <attachment-id> --out F
flowctl tracker wire list-open
```

`comment-update` / `comment-delete` require the parent locator: GitLab and Jira both need issue **and** comment id.

**Spec-aware verbs** - take a spec id, write local state and an event-tagged receipt:

```
flowctl tracker create           <spec-id> --title T --body-file F [--event E]   # spec exists, link it
flowctl tracker create-first     --title T --body-file F --retry-key K           # NO spec yet (fn-134 path)
flowctl tracker persist-external <spec-id> --identifier I [--id D] [--url U] --source mcp
flowctl tracker status           <spec-id> --to <normalized> [--reason R] [--event E]
flowctl tracker relate           <spec-id> --blocked-by <other-spec-id>
flowctl tracker sync-body        <spec-id> --flow-file F [--tracker-body-file T] [--direction push|pull]
```

### Lifecycle facades (what callers actually invoke)

The granular verbs above are the **mechanism**. Callers do not compose them: a touchpoint today says "push this spec" and gets create-if-unlinked, body orchestration, status, comment markers, dedup, receipts and event tagging as one unit. Exposing only granular verbs would push that orchestration into every calling skill as prose - which is the problem this batch exists to remove, and would make spec C's behavior-preserving teardown impossible.

```
flowctl tracker sync <spec-id> --op push|pull|reconcile|comment --event <perEvent-key> [--flow-file F] [--body-file B]
```

One facade, four ops, matching the existing `perEvent` value vocabulary exactly (`off | pull | push | reconcile | comment`). It owns: create-if-unlinked, the granular-verb sequence, comment marker + dedup, the event-tagged receipt, and structured conflict/degradation reporting. Content that requires judgment (a rendered body, a resolved merge, comment text) is passed **in** as a file - the facade never composes it.

**Spec C gates on these facades passing conformance**, not on the granular verbs.

### Command semantics (single source of truth)

| verb | takes | writes local state | receipt | `--event` | degradation |
|---|---|---|---|---|---|
| `wire *` | locator | no | **none** | n/a | `degraded` field on the result |
| `create` | spec id | `tracker.*` | yes | optional | `degraded` field |
| `create-first` | retry key, no spec | recovery record | **none** (no spec exists - fn-134 exception) | n/a | `degraded` field |
| `persist-external` | spec id | `tracker.*` | yes | optional | `degraded` field |
| `status` | spec id | `lastSyncedAt` | yes | optional | `degraded` field |
| `relate` | spec ids | `depRelations` | yes | optional | `degraded` field |
| `sync-body` | spec id | paired merge base | yes | optional | `degraded` field |

Wire verbs write no receipt because they have no spec id and `sync receipt` requires one. **Degradation is never a sentence in a receipt note** - it is the structured `degraded` field, and the receipt schema gains a matching structured field.

### `sync-body` takes the body; it never composes one

flowctl does **not** perform the semantic merge - that is the skill's judgment surface. So `sync-body` cannot be given only a spec id: it takes `--flow-file` (the agent's final rendered or conflict-resolved local body) and, on a two-way reconcile, `--tracker-body-file` (the agent-approved tracker-side body). flowctl writes what it is handed, reads back, and commits both merge-base halves atomically.

`--direction pull` snapshots both forms without writing to the tracker, so a pull-only reconcile still establishes a valid paired base. The result reports **which side was written**.

### The MCP boundary

flowctl cannot reach the MCP rung: `linear-mcp.md` states the tool surface is host-agent-visible with **no shell command**. The agent performs that call and hands the result to flowctl.

**Linear MCP returns the display identifier only, never the durable UUID** (`linear-mcp.md:100`). So `persist-external` accepts an identifier-only call and resolves the UUID via the GraphQL rung before persisting. If GraphQL is unreachable it persists an explicitly-marked **identifier-only linked state**. That needs a schema, because today `tracker.id: null` means *unlinked* and would be misread: the state is `tracker.linkState: "identifier_only"` alongside the populated `identifier`/`url` and a null `id`. Commands that require a durable id return `class: unresolved` against it rather than treating it as unlinked; **`tracker reconcile` is the named entry point** that resolves the UUID and atomically completes the record. It never fabricates a durable id and never silently omits one.

**MCP is restricted to create and discovery.** All other operations require GraphQL. This is a deliberate narrowing: a general "persist any externally-performed operation" contract would need per-operation state transitions and receipts for operations flowctl never saw, which is unbounded surface for one rung of one adapter.

### Body fidelity: server readback is canonical

Measured by posting one identical 391-byte markdown fixture to all four and diffing byte-for-byte:

| tracker | issue body | comment |
|---|---|---|
| Jira (v2) | byte-identical | identical |
| GitHub | byte-identical | identical |
| GitLab | **strips the trailing newline** | same |
| Linear | **rewrites the description** | identical |

Linear's rewriting, measured: `_italic_` to `*italic*`, `[l](url)` to `[l](<url>)`, `- bullet` to `* bullet`, `|---|---|` to `| -- | -- |`, `- [x]` to `- [X]`, trailing newline stripped. Comments untouched.

**The two halves are not the same body**, which the earlier draft got wrong by saying "the merge base equals the readback":

- `mergeBaseFlow` = the **exact final local spec body** (it must stay comparable to the local spec, or every subsequent flow-side diff is false)
- `mergeBaseTracker` = `trackerBodyForMerge(server readback)`

Storing the readback in both halves would make Linear's rewriting look like immediate flow-side divergence on the very next reconcile. Both hashes and snapshots commit **atomically, only after write and readback both succeed**. Client-side normalization is limited to a short enumerated set of stable transformations (trailing-newline) and does **not** attempt to predict Linear's rewriting - that is unsafe around code fences and escapes, and readback already supplies the authoritative body.

## Edge Cases & Constraints
<!-- scope: technical -->

Every item measured live on 2026-07-26:

- **No tracker dedups on create.** Identical title+body produced a second issue on GitHub, GitLab and Linear. The pre-create window (issue created, process dies before the recovery record is written) stays **open**, and is tested as open rather than asserted closed.
- **Jira attachment upload requires `X-Atlassian-Token: no-check`; omitting it returns 404**, not 403 - it reads as a wrong endpoint when it is a missing header.
- **Linear upload is two-step**: `fileUpload` -> presigned PUT with required headers -> reference `assetUrl`. Declared `size` must match the body exactly. Retrieval needs the auth header (401 without).
- **GitLab attachments are retrievable only via `GET /projects/:id/uploads/:upload_id`.** The `/uploads/<secret>/file` path in the returned markdown needs a session cookie; an API token gets 302 then 403 HTML.
- **GitHub has no attachment API** (`POST /issues/:n/uploads` -> 404). `capabilities.attachments` is false; the commit-and-link workaround is documented with its expiring-token caveat for private repos.
- **GitLab notes mix system notes with user comments** (`system: true` for "changed title"). Comment sync must filter or it ingests GitLab's own audit trail.
- **GitLab states are `opened`/`closed`**, not `open`/`closed`.
- **GitHub `state_reason` accepts an undocumented `duplicate`** (stored as `duplicate`); the docs list only `completed`/`not_planned`/`reopened`. Garbage 422s.
- **Linear labels must exist before attaching** (`issueLabelCreate` then `issueUpdate{labelIds}`); GitHub and GitLab create on demand.
- **GitHub `GET /issues` returns pull requests too** - filter on the `pull_request` key.
- **GitHub sub-issues exist** (`POST /issues/{n}/sub_issues`) - hierarchy, not blocked-by.
- **Jira Cloud cannot reproduce custom project keys** (`MY_PROJECT`, >10 chars); Cloud enforces uppercase-alphanumeric max-10. That path is implemented from prose and marked unverified.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** All wire verbs work against all four adapters through the injected executor, taking a **locator** and validating the returned durable id against it.
- **R2:** `comment-update` / `comment-delete` require and use the parent locator.
- **R3:** `create` (spec exists) and `create-first` (no spec, fn-134 recovery-record path) are separate verbs with the receipt semantics in the table. `create-first` preserves fn-134's no-duplicate-on-retry guarantee.
- **R4:** `persist-external` accepts an identifier-only MCP result and resolves the UUID via GraphQL before persisting. GraphQL unreachable -> explicitly-marked identifier-only state, never a fabricated or silently-missing durable id. A later reconcile completes it, and that completion is tested.
- **R5:** MCP is restricted to create/discovery; every other operation requires GraphQL, stated in the skill contract so no caller assumes otherwise.
- **R6:** `status` has a complete, stated state machine rather than a single sentence. `--to` is a **request, not an authority**: fn-66's merge-evidence gate decides the outcome, so terminal `Done` requires a GitHub-confirmed MERGED, `In Review` an open PR, and completion-review alone is never terminal. Allowed `--to`/`--reason` pairs are enumerated. Which local fields each branch may write is explicit: an **applied** write updates `lastSyncedAt` (and the local status where the ladder says the tracker wins); a **no-op, defer or conflict does NOT advance `lastSyncedAt`**, because advancing it would mark a sync that did not happen. Canceled-family transitions are **surfaced, never auto-applied**, so `--reason duplicate` on GitHub records the reason on an otherwise-legal close and never forces a cancel.
- **R7:** The who-wins ladder keeps **collision cases first**; a reordering test fails. Deadlock fallback and unmapped states have enumerated deterministic outcomes; anything genuinely ambiguous returns `class: conflict` for the skill's recovery surface rather than defaulting silently.
- **R8:** Jira status writes use the **cached target status id** but still `GET .../transitions` for the issue's current status first, because transition ids are valid only from the current status (`jira.md:738`, verified live). The cache buys correctness, not a saved round-trip. No legal transition to the target means **defer + receipt, never an illegal forced jump**. GitHub's `duplicate` reason is reachable via `--reason`.
- **R9:** Attachments upload **and retrieve byte-identically** on Jira, Linear and GitLab, each via its own documented route. GitHub records `attachments: false`.
- **R10:** `relate` reproduces **fn-64's full contract**: `depRelations` provenance ledger, additive-only, completed-blocker rule, never-clobber-on-collision (defer + queue), and `<!-- flow:deps -->` excluded from body-merge divergence hashing.
- **R11:** GitLab dependency projection uses `is_blocked_by` on Premium and above and degrades to `relates_to` on Free, with the degradation in the structured `degraded` field.
- **R12:** `sync-body` performs write + readback + paired merge base as **one transaction**. The merge base equals the readback, not the sent body. A partial failure leaves the prior merge base untouched. A no-op reconcile against an unmodified issue produces **no** diff on any of the four.
- **R13:** The paired merge-base snapshot invariant holds: both halves at one sync point, atomically, never per-flag.
- **R14:** Comment sync filters GitLab system notes (`system: true`).
- **R15:** The capability table is **already decided in spec A**; B implements it and does not re-open it. `deleteIssue` and `subIssues` are **kept**, with their consumers named here: `deleteIssue` gates cleanup paths (and is `false` on GitHub, which can only close `not_planned`); `subIssues` is consumed by dependency projection as GitHub's **degraded** form - and it is **hierarchy, not blocked-by**, so it must never be presented as a blocking relation. The two remaining behaviors are decided rather than deferred: an unknown Linear label is **auto-created** (matching GitHub/GitLab create-on-demand, so callers need no per-provider branch); a repeated `--add` on a single-assignee tracker **replaces** and reports the replacement in `degraded`.
- **R16:** Jira body operations use **apiVersion 2** on Cloud and Data Center; a plain-string body round-trips byte-exact and the ADF conversion for v3 readers is Jira's own.
- **R17:** The Jira Data Center custom-key path is implemented from prose and **marked unverified in code comment and spec**. Its live smoke is a separate externally-blocked follow-up, not a task here - a permanently-`todo` task would block spec close.
- **R19:** The lifecycle facade `tracker sync <spec-id> --op push|pull|reconcile|comment --event E` exists and is conformance-tested per adapter. It reproduces today's touchpoint behavior as one unit - create-if-unlinked, granular sequence, comment marker + dedup, event-tagged receipt, structured conflict/degradation - so a caller replaces a dispatch with a single call and no orchestration prose. Judgment-bearing content is passed in as a file; the facade never composes it.
- **R18:** A **cross-adapter conformance matrix** covers every verb on all four adapters, plus fault injection for: the open pre-create window, post-write readback failure, scoped invalidation, lock race, retry exhaustion, rate-limit backoff. Focused regression tests live with the code; this matrix is the cross-cutting layer.

## Boundaries
<!-- scope: business -->

**In scope:** the verb surface, capability-gated operations, body fidelity and merge-base transactions, the conformance matrix.

**Out of scope:**
- Distribution, executor, resolved cache - spec **A** (fn-139).
- Prose teardown, dispatch removal, docs, baselines - spec **C**.
- **Body-merge conflict adjudication**, which stays agentic. Memory `plan-sync-skip-gate-not-viable` records a deterministic gate that was built, evaluated and killed by its own eval; body reconciliation is more semantic than that, not less. Any task proposing to make conflict resolution deterministic is out of scope by construction.
- Closing the pre-create window.
- Batching.

## Decision Context
<!-- scope: both -->

### Why a locator rather than making wire verbs spec-aware

The alternative was to give every verb a spec id. Rejected on two grounds: it forces a local spec to exist for operations that legitimately have none (reading an issue **during discovery**, before any spec is minted), and it collapses the wire/spec-aware split that fixed the incoherent "every command writes a receipt" rule. The locator also buys durable-id validation on response, which is what catches a project move.

### Why MCP is narrowed rather than generalized

A general external-operation persistence contract would need per-operation state transitions and receipts for operations flowctl never observed - unbounded surface for one rung of one adapter. Restricting MCP to create/discovery keeps the boundary small and honest, and GraphQL covers everything else for Linear.

### Why readback is canonical rather than client-side normalization

Linear rewrites descriptions on write in at least six measured ways. Predicting that client-side is unsafe around code fences and escapes and would need updating whenever Linear changes. The post-write readback already **is** the authoritative body, so it becomes the merge base. Client normalization is limited to trailing-newline, which is stable and adapter-agnostic.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_tracker_sync_state test_tracker_sync_gitlab test_tracker_sync_jira -q
```

Full gate once at completion: `python3 scripts/run_tests_parallel.py`
