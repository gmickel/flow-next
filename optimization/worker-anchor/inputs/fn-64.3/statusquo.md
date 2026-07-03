$ flowctl show fn-64-tracker-sync-project-flow-spec.3 --json
{
  "success": true,
  "assignee": "gordon.mickel@gmail.com",
  "claim_note": "",
  "claimed_at": "2026-06-17T01:59:47.286055Z",
  "created_at": "2026-06-16T15:27:50.438599Z",
  "depends_on": [
    "fn-64-tracker-sync-project-flow-spec.2"
  ],
  "id": "fn-64-tracker-sync-project-flow-spec.3",
  "priority": null,
  "spec": "fn-64-tracker-sync-project-flow-spec",
  "spec_path": ".flow/tasks/fn-64-tracker-sync-project-flow-spec.3.md",
  "status": "done",
  "title": "Linear adapter relation transport (MCP save_issue + GraphQL issueRelationCreate, read-before-write dedup)",
  "updated_at": "2026-06-17T02:09:06.940901Z",
  "evidence": {
    "commits": [
      "08cb57beb6c65bca36f405e392f167f2e52a0323"
    ],
    "prs": [],
    "tests": [
      "docs-as-implementation (Linear adapter reference files) \u2014 no test suite; impl-review RP backend SHIP, 0 findings, R1+R3 covered"
    ]
  },
  "impl": null,
  "review": null,
  "sync": null,
  "epic": "fn-64-tracker-sync-project-flow-spec"
}

$ flowctl cat fn-64-tracker-sync-project-flow-spec.3
# fn-64-tracker-sync-project-flow-spec.3 Linear adapter relation transport (MCP save_issue + GraphQL issueRelationCreate, read-before-write dedup)

## Description
### Goal
Implement the relation transport on the Linear adapter ladder (MCP + GraphQL rungs), with read-before-write dedup. **Satisfies R1, R3.**

### Investigation targets
- `references/adapter-interface.md` — the `setIssueRelation`/`listIssueRelations` contract from fn-64.2.
- `references/linear-mcp.md:27` `save_issue` (exposes `blockedBy`/`blocks`, append-only) + `:28` `get_issue` `includeRelations:true` (read path). MCP rung: `setIssueRelation` via `save_issue` blockedBy; `listIssueRelations` via `get_issue` includeRelations.
- `references/linear-graphql.md:93-118` mutations — add `issueRelationCreate(input:{issueId, relatedIssueId, type: blocks})`. "A blocked by B" = `blocks` edge with `issueId:B, relatedIssueId:A`. Enum is lowercase `blocks`/`related`/`duplicate` — do NOT invent `blocked_by`.
- List/dedup: query BOTH `relations { nodes {...} }` AND `inverseRelations { nodes {...} }` — each REQUIRES an explicit `first:` arg (memory: linear-graphql-every-nodes-connection) or Linear rejects the query. Canonicalize each edge to one direction before comparing to avoid silent inverse-duplicates.
- `references/linear-ladder.md` — place the new method in the MCP→GraphQL→no-op ladder; bottom rung no-ops + `noop` receipt.
## Acceptance
- [ ] MCP rung: `setIssueRelation` via `save_issue` blockedBy/blocks — but FIRST re-verify the pinned MCP schema actually exposes these params (it drifts); if absent, fall back to the GraphQL rung when `LINEAR_API_KEY` is set, else write a `noop` receipt.
- [ ] GraphQL rung: `issueRelationCreate(input:{issueId, relatedIssueId, type: blocks})` with correct operand direction ("A blocked by B" = issueId:B, relatedIssueId:A).
- [ ] Dedup (read-before-write): list via BOTH `relations` AND `inverseRelations` (each with explicit `first:`), canonicalize each edge to one direction before comparing; re-run creates no duplicate (R3).
- [ ] Bottom rung no-ops with a `noop` receipt (not "deferred").
- [ ] linear-mcp.md / linear-graphql.md / linear-ladder.md updated with exact mutation/field names, verified against the live schema.
## Done summary
Implemented the Linear adapter relation transport for dependency projection across the three rung references: MCP rung (`setIssueRelation` via `save_issue` `blockedBy` append-only, live-re-verified schema; `listIssueRelations` via `get_issue includeRelations:true`), GraphQL rung (`issueRelationCreate(type: blocks)` with correct "A blocked by B" operand inversion `issueId:B`/`relatedIssueId:A`, dedup across BOTH `relations`+`inverseRelations` with explicit `first:` canonicalized to one direction), and the ladder (per-capability MCP-schema-drift fallback to GraphQL/noop, never-delete-non-ours, noop bottom rung). Read-before-write idempotency mandated on every rung. Satisfies R1, R3.
## Evidence
- Commits: 08cb57beb6c65bca36f405e392f167f2e52a0323
- Tests: docs-as-implementation (Linear adapter reference files) — no test suite; impl-review RP backend SHIP, 0 findings, R1+R3 covered
- PRs:

$ flowctl show fn-64-tracker-sync-project-flow-spec --json
{
  "success": true,
  "branch_name": "fn-64-tracker-sync-project-flow-spec",
  "completion_review_status": "ship",
  "completion_reviewed_at": "2026-06-17T02:54:00.198874Z",
  "created_at": "2026-06-16T15:15:26.005541Z",
  "default_impl": null,
  "default_review": null,
  "default_sync": null,
  "depends_on_epics": [
    "fn-52-tracker-sync-bridge-project-flow-specs",
    "fn-57-tracker-sync-lifecycle-hooks-forcing",
    "fn-58-spec-readiness-signal-ready-flag"
  ],
  "id": "fn-64-tracker-sync-project-flow-spec",
  "next_task": 1,
  "plan_review_status": "ship",
  "plan_reviewed_at": "2026-06-16T15:40:34.145142Z",
  "ready": true,
  "spec_path": ".flow/specs/fn-64-tracker-sync-project-flow-spec.md",
  "status": "done",
  "title": "tracker-sync: project Flow spec dependencies into Linear issue relations",
  "tracker": {
    "baseHashFlow": "593cef053e652e12cf34ec0e1683f903af5b479891127e704eeda5fe67ec58ae",
    "baseHashTracker": "593cef053e652e12cf34ec0e1683f903af5b479891127e704eeda5fe67ec58ae",
    "depRelations": [],
    "id": "FLOW-14",
    "identifier": "FLOW-14",
    "lastSyncedAt": "2026-06-16T15:20:39.978514Z",
    "mergeBaseFlow": "\n> **Origin:** Linear issue [FLOW-14](https://linear.app/gmickel/issue/FLOW-14) (team Flow Next, project Development), authored 2026-06-16. Grabbed via `/flow-next:tracker-sync`; this spec is the canonical source of truth and FLOW-14 is its co-editable mirror. **Scope extended beyond the original issue:** dependency projection must cover **both** the Linear adapter AND the GitHub adapter, not Linear alone (Gordon, 2026-06-16).\n\n## Goal & Context\n\nFlow specs can declare cross-spec dependencies in local `.flow` metadata via `depends_on_epics` (the dep edges surfaced by `flowctl dep` / shown in `flowctl show`). When those specs are linked to tracker issues through the tracker-sync bridge, the dependency graph stays **local-only**: nothing projects the edges onto the tracker, so the board shows independent issues even though Flow knows one blocks another.\n\nThis bit us in SapienXT: Flow showed `fn-27` and `wor-24` depending on `fn-26`, and `fn-29` depending on `fn-15`/`fn-16`/`fn-23`, but Linear showed no corresponding issue relations until someone added them by hand (`WOR-24`\u2192`WOR-25`, `WOR-26`\u2192`WOR-25`, `WOR-27`\u2192`WOR-12`/`WOR-13`/`WOR-18`). The board misrepresents the real ordering, and teams that live in the tracker can't see what's actually blocked.\n\n**Goal:** extend tracker-sync so linked Flow spec dependencies are projected to tracker issue relations automatically \u2014 a `depends_on_epics` edge between two linked specs becomes a **blocked-by** relation between their issues \u2014 on **both** Linear and GitHub, idempotently, without clobbering relations a human added by hand. This belongs in tracker-sync, not in per-repo workaround logic.\n\n## Architecture & Data Models\n\nThe bridge is the `flow-next-tracker-sync` skill (transport-blind spine in `steps.md`) plus deterministic `flowctl sync` plumbing and two adapters: the Linear ladder (MCP \u2192 GraphQL \u2192 no-op, `references/linear-ladder.md`) and the GitHub `gh` adapter (`references/github.md`). Dependency projection slots in as a **new transport-blind reconcile-time hook** on the linked-spec push/reconcile path \u2014 the skill resolves the edges and calls the normalized relation transport; each adapter implements it in its own fidelity.\n\n- **Edge source (transport-blind).** Read `depends_on_epics` from the spec being synced. Each entry is a flow spec id (the dep target). flowctl enumerates the edges + resolves each dep spec's tracker link from sync state.\n- **Link resolution.** For each dependency spec id, resolve its linked tracker issue from sync state (the `tracker.id` / `identifier` the dep spec carries). A dependency spec with no tracker link is **unresolvable** \u2192 surfaced as a warning naming the dep spec id, never silently dropped.\n- **Relation projection (normalized).** For each resolved (current-issue, dep-issue) pair, ensure a **blocked-by** relation exists (current issue blocked by dep issue). Driven through a new normalized transport pair on the adapter interface \u2014 `setIssueRelation(from, to, type=\"blocks\")` + `listIssueRelations(issue)` \u2014 that both adapters implement:\n  - **Linear adapter:** native issue relations. MCP rung uses the relation API; GraphQL rung the `issueRelationCreate` mutation (`type: blocks`); bottom rung no-ops with a deferred receipt. Idempotency via `listIssueRelations` pre-check.\n  - **GitHub adapter:** prefer GitHub's **native issue dependencies** (\"blocked by\" / \"blocks\") via `gh api` GraphQL where the repo/account has them; **fall back to a body-rendered, fenced \"Blocked by\" block** (e.g. a `<!-- flow-next:deps -->`-delimited list of `#N` references) when native dependencies are unavailable \u2014 the reduced-fidelity posture the GitHub adapter already takes for status. The fenced block is the provenance boundary on the fallback path (only lines inside the marker are ours).\n- **Provenance marking.** Flow-projected relations must be distinguishable from human-created ones so cleanup never removes a manual relation. Record which relations tracker-sync created in sync state (a per-pair ledger, mirroring the existing merge-base / `lastSyncedAt` model) so projection is idempotent and removals are provably-ours-only. On the GitHub fenced-block fallback, the marker delimits provenance; on native relations (Linear, GitHub-native), the ledger does.\n- **Completed-blocker semantics.** A dependency whose issue is Done/Closed is a **historical/completed blocker**: the relation stays visible on the tracker but must NOT feed back into Flow `ready=true` gating (readiness already treats done deps as satisfied \u2014 this hook must not regress that).\n\n## API Contracts\n\n- **flowctl plumbing** (deterministic, transport-blind): enumerate a spec's dependency edges with their resolved tracker links, e.g. `flowctl sync list-dep-relations <spec-id> --json` \u2192 `[{dep_spec, dep_tracker_id, dep_identifier, dep_status, projected: bool}]`; record/read projected-relation provenance (`sync set-dep-relation` / `sync clear-dep-relation`, or folded into the existing sync-state struct).\n- **Adapter transport contract** (added to `references/adapter-interface.md`): normalized `setIssueRelation(fromIssue, toIssue, type=\"blocks\")` + `listIssueRelations(issue) -> [{from, to, type, source}]`, implemented by BOTH adapters. Idempotency: check `listIssueRelations` before create; never create a duplicate. `source` distinguishes ours-vs-theirs where the transport can.\n- **Linear rungs:** MCP relation API + GraphQL `issueRelationCreate`; no-op + deferred receipt on the bottom rung.\n- **GitHub rungs:** native issue-dependencies via `gh api` GraphQL when present; fenced `Blocked by` body block via the existing `gh` body-write path otherwise (single rung + no-op, reduced fidelity \u2014 same shape the adapter uses for status).\n- **Warning surface:** missing tracker link on a dependency spec \u2192 a warning line naming the dependency spec id (and the parent spec), in the skill report and on the `sync receipt`.\n\n## Edge Cases & Constraints\n\n- **Idempotent rerun:** re-running tracker-sync over an already-projected dependency creates zero new relations / appends nothing to the GitHub fenced block (pre-check via `listIssueRelations` + the provenance ledger / marker).\n- **Missing dependency link:** dep spec not linked to any issue \u2192 warning naming the dep spec id; the rest of the sync proceeds (item-level failure isolation, as elsewhere in the bridge).\n- **Completed dependency:** dep issue Done/Closed \u2192 relation remains visible as a completed blocker but does not block `ready=true` handling.\n- **Manual relations preserved:** a relation tracker-sync cannot prove it created (not in the ledger / outside the fenced block) is never removed \u2014 on either adapter.\n- **Transport unavailable / reduced-fidelity:** no transport reachable \u2192 projection skipped with a deferred/errored receipt, never blocking the lifecycle; GitHub without native dependencies \u2192 fenced-block fallback, not a hard failure.\n- **No self/cycle relations:** never project a relation from an issue to itself; tolerate (don't crash on) a dependency cycle in the flow graph.\n- **Cross-adapter consistency:** the normalized hook behaves identically from the skill's view regardless of adapter; only fidelity differs (native relation vs fenced body block).\n\n## Acceptance Criteria\n\n- **R1:** A Flow spec with `depends_on_epics` whose dependency specs are linked to tracker issues creates matching **blocked-by** relations (current issue blocked by each dependency issue) on sync \u2014 verified on the **Linear** adapter (native relations).\n- **R2:** The same projection works on the **GitHub** adapter \u2014 native issue dependencies where available, else a provenance-fenced \"Blocked by\" block of `#N` references in the issue body.\n- **R3:** Re-running tracker-sync is idempotent on both adapters \u2014 no duplicate relations, no duplicated fenced-block entries.\n- **R4:** A dependency spec with no tracker link is surfaced as a warning that names the dependency spec id; the sync otherwise completes.\n- **R5:** A Done/Closed dependency issue remains visible as a completed blocker relation but does NOT block `ready=true` handling for the dependent spec.\n- **R6:** Existing tracker relations that tracker-sync cannot prove it created are preserved (never removed by projection or teardown) \u2014 on both adapters (ledger for native relations, fenced marker for the GitHub fallback).\n- **R7:** Projection is provenance-tracked \u2014 tracker-sync records which relations it created so add / idempotent-rerun / safe-removal can rely on it.\n- **R8:** The relation hook is exposed through the normalized adapter interface (`setIssueRelation` / `listIssueRelations`) and is transport-blind in the skill \u2014 the skill code does not branch on Linear-vs-GitHub.\n- **R9:** Unit or integration coverage proves, per adapter: relation add, idempotent rerun (no dup), missing-link warning, and completed-blocker behavior; plus the GitHub native-vs-fallback path selection.\n- **R10:** Docs updated \u2014 `plugins/flow-next/docs/tracker-sync.md`, `references/adapter-interface.md`, `references/linear-ladder.md`, and `references/github.md` describe dependency-relation projection, the provenance model, the GitHub native-vs-fenced-fallback behavior, and the completed-blocker semantics; the flow-next.dev tracker-sync page is updated in the same workstream.\n\n## Boundaries\n\n- **No new dependency authoring** \u2014 this projects existing `depends_on_epics` edges; it does not add a way to declare deps from the tracker side (tracker\u2192flow dep ingestion is out of scope).\n- **No stale-relation deletion beyond the provenance-safe case** \u2014 if a `depends_on_epics` edge is removed from a spec, cleaning up the now-stale projected relation is a follow-up; R6 only mandates we never remove non-ours. Removing ours-but-stale is optional/best-effort.\n- **No readiness-model changes** \u2014 `ready=true` gating already treats done deps as satisfied; this spec must not alter that, only avoid regressing it.\n- **GitHub Projects fields** (status columns, custom dependency fields) are out of scope \u2014 issue-level dependencies / body-block only.\n\n## Decision Context\n\nThis belongs in tracker-sync, not per-repo workaround logic, because the dependency graph is a first-class Flow artifact and the bridge's whole job is projection (body, status, comments already sync two-way \u2014 relations are the missing edge type). SapienXT hand-added relations as a stopgap; that doesn't scale and drifts the moment the flow graph changes.\n\n**Both adapters, one hook.** The original issue framed this as Linear-only; Gordon extended it to GitHub too. The right shape is a single transport-blind relation hook on the adapter interface, implemented at each adapter's native fidelity \u2014 Linear has first-class issue relations; GitHub has native issue dependencies in some accounts and a body-block fallback otherwise. Keeping the skill transport-blind (R8) means the dependency logic lives once and both trackers inherit it, exactly as body/status/comments sync already do.\n\n**blocked-by is the right direction:** Flow's `depends_on_epics` means \"this spec depends on / is blocked by those\" \u2014 a direct semantic match to the blocked-by/blocks relation pair on both trackers, so no inversion ambiguity.\n\n**Provenance over diff-reconcile:** rather than diffing all relations and reconciling, we only ever touch relations we can prove we created (ledger for native, fenced marker for the GitHub fallback). The cost of wrongly deleting a human's manual relation is high and silent, so we stay conservative \u2014 mirroring the bridge's existing \"surface diffs, never overwrite\" posture.\n\n**Completed-blocker handling** is explicit because naive projection (drop the relation once the dep is Done) would erase real historical ordering from the board; keeping it visible while not re-gating readiness preserves both the audit trail and the existing readiness semantics.\n",
    "mergeBaseTracker": "\n> **Origin:** Linear issue [FLOW-14](https://linear.app/gmickel/issue/FLOW-14) (team Flow Next, project Development), authored 2026-06-16. Grabbed via `/flow-next:tracker-sync`; this spec is the canonical source of truth and FLOW-14 is its co-editable mirror. **Scope extended beyond the original issue:** dependency projection must cover **both** the Linear adapter AND the GitHub adapter, not Linear alone (Gordon, 2026-06-16).\n\n## Goal & Context\n\nFlow specs can declare cross-spec dependencies in local `.flow` metadata via `depends_on_epics` (the dep edges surfaced by `flowctl dep` / shown in `flowctl show`). When those specs are linked to tracker issues through the tracker-sync bridge, the dependency graph stays **local-only**: nothing projects the edges onto the tracker, so the board shows independent issues even though Flow knows one blocks another.\n\nThis bit us in SapienXT: Flow showed `fn-27` and `wor-24` depending on `fn-26`, and `fn-29` depending on `fn-15`/`fn-16`/`fn-23`, but Linear showed no corresponding issue relations until someone added them by hand (`WOR-24`\u2192`WOR-25`, `WOR-26`\u2192`WOR-25`, `WOR-27`\u2192`WOR-12`/`WOR-13`/`WOR-18`). The board misrepresents the real ordering, and teams that live in the tracker can't see what's actually blocked.\n\n**Goal:** extend tracker-sync so linked Flow spec dependencies are projected to tracker issue relations automatically \u2014 a `depends_on_epics` edge between two linked specs becomes a **blocked-by** relation between their issues \u2014 on **both** Linear and GitHub, idempotently, without clobbering relations a human added by hand. This belongs in tracker-sync, not in per-repo workaround logic.\n\n## Architecture & Data Models\n\nThe bridge is the `flow-next-tracker-sync` skill (transport-blind spine in `steps.md`) plus deterministic `flowctl sync` plumbing and two adapters: the Linear ladder (MCP \u2192 GraphQL \u2192 no-op, `references/linear-ladder.md`) and the GitHub `gh` adapter (`references/github.md`). Dependency projection slots in as a **new transport-blind reconcile-time hook** on the linked-spec push/reconcile path \u2014 the skill resolves the edges and calls the normalized relation transport; each adapter implements it in its own fidelity.\n\n- **Edge source (transport-blind).** Read `depends_on_epics` from the spec being synced. Each entry is a flow spec id (the dep target). flowctl enumerates the edges + resolves each dep spec's tracker link from sync state.\n- **Link resolution.** For each dependency spec id, resolve its linked tracker issue from sync state (the `tracker.id` / `identifier` the dep spec carries). A dependency spec with no tracker link is **unresolvable** \u2192 surfaced as a warning naming the dep spec id, never silently dropped.\n- **Relation projection (normalized).** For each resolved (current-issue, dep-issue) pair, ensure a **blocked-by** relation exists (current issue blocked by dep issue). Driven through a new normalized transport pair on the adapter interface \u2014 `setIssueRelation(from, to, type=\"blocks\")` + `listIssueRelations(issue)` \u2014 that both adapters implement:\n  - **Linear adapter:** native issue relations. MCP rung uses the relation API; GraphQL rung the `issueRelationCreate` mutation (`type: blocks`); bottom rung no-ops with a deferred receipt. Idempotency via `listIssueRelations` pre-check.\n  - **GitHub adapter:** prefer GitHub's **native issue dependencies** (\"blocked by\" / \"blocks\") via `gh api` GraphQL where the repo/account has them; **fall back to a body-rendered, fenced \"Blocked by\" block** (e.g. a `<!-- flow-next:deps -->`-delimited list of `#N` references) when native dependencies are unavailable \u2014 the reduced-fidelity posture the GitHub adapter already takes for status. The fenced block is the provenance boundary on the fallback path (only lines inside the marker are ours).\n- **Provenance marking.** Flow-projected relations must be distinguishable from human-created ones so cleanup never removes a manual relation. Record which relations tracker-sync created in sync state (a per-pair ledger, mirroring the existing merge-base / `lastSyncedAt` model) so projection is idempotent and removals are provably-ours-only. On the GitHub fenced-block fallback, the marker delimits provenance; on native relations (Linear, GitHub-native), the ledger does.\n- **Completed-blocker semantics.** A dependency whose issue is Done/Closed is a **historical/completed blocker**: the relation stays visible on the tracker but must NOT feed back into Flow `ready=true` gating (readiness already treats done deps as satisfied \u2014 this hook must not regress that).\n\n## API Contracts\n\n- **flowctl plumbing** (deterministic, transport-blind): enumerate a spec's dependency edges with their resolved tracker links, e.g. `flowctl sync list-dep-relations <spec-id> --json` \u2192 `[{dep_spec, dep_tracker_id, dep_identifier, dep_status, projected: bool}]`; record/read projected-relation provenance (`sync set-dep-relation` / `sync clear-dep-relation`, or folded into the existing sync-state struct).\n- **Adapter transport contract** (added to `references/adapter-interface.md`): normalized `setIssueRelation(fromIssue, toIssue, type=\"blocks\")` + `listIssueRelations(issue) -> [{from, to, type, source}]`, implemented by BOTH adapters. Idempotency: check `listIssueRelations` before create; never create a duplicate. `source` distinguishes ours-vs-theirs where the transport can.\n- **Linear rungs:** MCP relation API + GraphQL `issueRelationCreate`; no-op + deferred receipt on the bottom rung.\n- **GitHub rungs:** native issue-dependencies via `gh api` GraphQL when present; fenced `Blocked by` body block via the existing `gh` body-write path otherwise (single rung + no-op, reduced fidelity \u2014 same shape the adapter uses for status).\n- **Warning surface:** missing tracker link on a dependency spec \u2192 a warning line naming the dependency spec id (and the parent spec), in the skill report and on the `sync receipt`.\n\n## Edge Cases & Constraints\n\n- **Idempotent rerun:** re-running tracker-sync over an already-projected dependency creates zero new relations / appends nothing to the GitHub fenced block (pre-check via `listIssueRelations` + the provenance ledger / marker).\n- **Missing dependency link:** dep spec not linked to any issue \u2192 warning naming the dep spec id; the rest of the sync proceeds (item-level failure isolation, as elsewhere in the bridge).\n- **Completed dependency:** dep issue Done/Closed \u2192 relation remains visible as a completed blocker but does not block `ready=true` handling.\n- **Manual relations preserved:** a relation tracker-sync cannot prove it created (not in the ledger / outside the fenced block) is never removed \u2014 on either adapter.\n- **Transport unavailable / reduced-fidelity:** no transport reachable \u2192 projection skipped with a deferred/errored receipt, never blocking the lifecycle; GitHub without native dependencies \u2192 fenced-block fallback, not a hard failure.\n- **No self/cycle relations:** never project a relation from an issue to itself; tolerate (don't crash on) a dependency cycle in the flow graph.\n- **Cross-adapter consistency:** the normalized hook behaves identically from the skill's view regardless of adapter; only fidelity differs (native relation vs fenced body block).\n\n## Acceptance Criteria\n\n- **R1:** A Flow spec with `depends_on_epics` whose dependency specs are linked to tracker issues creates matching **blocked-by** relations (current issue blocked by each dependency issue) on sync \u2014 verified on the **Linear** adapter (native relations).\n- **R2:** The same projection works on the **GitHub** adapter \u2014 native issue dependencies where available, else a provenance-fenced \"Blocked by\" block of `#N` references in the issue body.\n- **R3:** Re-running tracker-sync is idempotent on both adapters \u2014 no duplicate relations, no duplicated fenced-block entries.\n- **R4:** A dependency spec with no tracker link is surfaced as a warning that names the dependency spec id; the sync otherwise completes.\n- **R5:** A Done/Closed dependency issue remains visible as a completed blocker relation but does NOT block `ready=true` handling for the dependent spec.\n- **R6:** Existing tracker relations that tracker-sync cannot prove it created are preserved (never removed by projection or teardown) \u2014 on both adapters (ledger for native relations, fenced marker for the GitHub fallback).\n- **R7:** Projection is provenance-tracked \u2014 tracker-sync records which relations it created so add / idempotent-rerun / safe-removal can rely on it.\n- **R8:** The relation hook is exposed through the normalized adapter interface (`setIssueRelation` / `listIssueRelations`) and is transport-blind in the skill \u2014 the skill code does not branch on Linear-vs-GitHub.\n- **R9:** Unit or integration coverage proves, per adapter: relation add, idempotent rerun (no dup), missing-link warning, and completed-blocker behavior; plus the GitHub native-vs-fallback path selection.\n- **R10:** Docs updated \u2014 `plugins/flow-next/docs/tracker-sync.md`, `references/adapter-interface.md`, `references/linear-ladder.md`, and `references/github.md` describe dependency-relation projection, the provenance model, the GitHub native-vs-fenced-fallback behavior, and the completed-blocker semantics; the flow-next.dev tracker-sync page is updated in the same workstream.\n\n## Boundaries\n\n- **No new dependency authoring** \u2014 this projects existing `depends_on_epics` edges; it does not add a way to declare deps from the tracker side (tracker\u2192flow dep ingestion is out of scope).\n- **No stale-relation deletion beyond the provenance-safe case** \u2014 if a `depends_on_epics` edge is removed from a spec, cleaning up the now-stale projected relation is a follow-up; R6 only mandates we never remove non-ours. Removing ours-but-stale is optional/best-effort.\n- **No readiness-model changes** \u2014 `ready=true` gating already treats done deps as satisfied; this spec must not alter that, only avoid regressing it.\n- **GitHub Projects fields** (status columns, custom dependency fields) are out of scope \u2014 issue-level dependencies / body-block only.\n\n## Decision Context\n\nThis belongs in tracker-sync, not per-repo workaround logic, because the dependency graph is a first-class Flow artifact and the bridge's whole job is projection (body, status, comments already sync two-way \u2014 relations are the missing edge type). SapienXT hand-added relations as a stopgap; that doesn't scale and drifts the moment the flow graph changes.\n\n**Both adapters, one hook.** The original issue framed this as Linear-only; Gordon extended it to GitHub too. The right shape is a single transport-blind relation hook on the adapter interface, implemented at each adapter's native fidelity \u2014 Linear has first-class issue relations; GitHub has native issue dependencies in some accounts and a body-block fallback otherwise. Keeping the skill transport-blind (R8) means the dependency logic lives once and both trackers inherit it, exactly as body/status/comments sync already do.\n\n**blocked-by is the right direction:** Flow's `depends_on_epics` means \"this spec depends on / is blocked by those\" \u2014 a direct semantic match to the blocked-by/blocks relation pair on both trackers, so no inversion ambiguity.\n\n**Provenance over diff-reconcile:** rather than diffing all relations and reconciling, we only ever touch relations we can prove we created (ledger for native, fenced marker for the GitHub fallback). The cost of wrongly deleting a human's manual relation is high and silent, so we stay conservative \u2014 mirroring the bridge's existing \"surface diffs, never overwrite\" posture.\n\n**Completed-blocker handling** is explicit because naive projection (drop the relation once the dep is Done) would erase real historical ordering from the board; keeping it visible while not re-gating readiness preserves both the audit trail and the existing readiness semantics.\n",
    "url": "https://linear.app/gmickel/issue/FLOW-14"
  },
  "updated_at": "2026-06-17T06:59:32.918649Z",
  "tasks": [
    {
      "id": "fn-64-tracker-sync-project-flow-spec.1",
      "title": "flowctl: depRelations sync state + list/set/clear-dep-relation subcommands + unit tests",
      "status": "done",
      "priority": null,
      "depends_on": []
    },
    {
      "id": "fn-64-tracker-sync-project-flow-spec.2",
      "title": "Adapter interface contract: setIssueRelation / listIssueRelations + relation struct",
      "status": "done",
      "priority": null,
      "depends_on": []
    },
    {
      "id": "fn-64-tracker-sync-project-flow-spec.3",
      "title": "Linear adapter relation transport (MCP save_issue + GraphQL issueRelationCreate, read-before-write dedup)",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-64-tracker-sync-project-flow-spec.2"
      ]
    },
    {
      "id": "fn-64-tracker-sync-project-flow-spec.4",
      "title": "GitHub adapter relation transport (native REST deps + fenced body-block fallback, #N parsing)",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-64-tracker-sync-project-flow-spec.2"
      ]
    },
    {
      "id": "fn-64-tracker-sync-project-flow-spec.5",
      "title": "projectDepRelations transport-blind skill hook (steps.md/SKILL.md): push+reconcile, warnings, completed-blocker, never-clobber, receipts",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-64-tracker-sync-project-flow-spec.1",
        "fn-64-tracker-sync-project-flow-spec.2",
        "fn-64-tracker-sync-project-flow-spec.3",
        "fn-64-tracker-sync-project-flow-spec.4"
      ]
    },
    {
      "id": "fn-64-tracker-sync-project-flow-spec.6",
      "title": "Docs + GLOSSARY + CHANGELOG + version bump + codex mirror regen + flow-next.dev",
      "status": "done",
      "priority": null,
      "depends_on": [
        "fn-64-tracker-sync-project-flow-spec.1",
        "fn-64-tracker-sync-project-flow-spec.5"
      ]
    }
  ]
}

$ flowctl cat fn-64-tracker-sync-project-flow-spec
# fn-64 tracker-sync: project Flow spec dependencies into tracker issue relations (Linear + GitHub)

> **Origin:** Linear issue [FLOW-14](https://linear.app/gmickel/issue/FLOW-14) (team Flow Next, project Development), authored 2026-06-16. Grabbed via `/flow-next:tracker-sync`; this spec is the canonical source of truth and FLOW-14 is its co-editable mirror. **Scope extended beyond the original issue:** dependency projection must cover **both** the Linear adapter AND the GitHub adapter, not Linear alone (Gordon, 2026-06-16).

## Goal & Context

Flow specs can declare cross-spec dependencies in local `.flow` metadata via `depends_on_epics` (the dep edges surfaced by `flowctl dep` / shown in `flowctl show`). When those specs are linked to tracker issues through the tracker-sync bridge, the dependency graph stays **local-only**: nothing projects the edges onto the tracker, so the board shows independent issues even though Flow knows one blocks another.

This bit us in SapienXT: Flow showed `fn-27` and `wor-24` depending on `fn-26`, and `fn-29` depending on `fn-15`/`fn-16`/`fn-23`, but Linear showed no corresponding issue relations until someone added them by hand (`WOR-24`→`WOR-25`, `WOR-26`→`WOR-25`, `WOR-27`→`WOR-12`/`WOR-13`/`WOR-18`). The board misrepresents the real ordering, and teams that live in the tracker can't see what's actually blocked.

**Goal:** extend tracker-sync so linked Flow spec dependencies are projected to tracker issue relations automatically — a `depends_on_epics` edge between two linked specs becomes a **blocked-by** relation between their issues — on **both** Linear and GitHub, idempotently, without clobbering relations a human added by hand. This belongs in tracker-sync, not in per-repo workaround logic.

## Architecture & Data Models

The bridge is the `flow-next-tracker-sync` skill (transport-blind spine in `steps.md`) plus deterministic `flowctl sync` plumbing and two adapters: the Linear ladder (MCP → GraphQL → no-op, `references/linear-ladder.md`) and the GitHub `gh` adapter (`references/github.md`). Dependency projection slots in as a **new transport-blind reconcile-time hook** (`projectDepRelations`, modelled on the existing one-way `projectReadiness` pull) on the linked-spec push/reconcile path — the skill resolves the edges and calls the normalized relation transport; each adapter implements it at its own fidelity.

- **Edge source + state (flowctl, deterministic).** Read `depends_on_epics` from the spec being synced. A new `depRelations` provenance list is added to the per-spec tracker state (`default_spec_tracker_state()`, persisted in the `.flow/specs/<id>.json` sidecar — NOT frontmatter), written atomically via the existing `_write_sync_state` / `atomic_write_json` helpers. **`depRelations[]` entry shape** (defined before coding): `{key: <stable opaque token>, dep_spec: <flow id>, from_tracker_id, to_tracker_id, type: "blocks", source: "flow", updatedAt}` — the `key` is an opaque hash (never a raw issue key inline; trackers auto-linkify keys even in HTML comments). `dep_status` in listings is the **local dep-spec status** from flowctl (`done`/`open`/…), NOT a remote fetch — flow is authoritative and the completed-blocker rule keys off the local dep spec being `done`.
- **Link resolution.** For each dependency spec id, resolve its linked tracker issue from sync state (`_iter_tracker_states()` → the dep spec's `tracker.id` / `identifier`). A dependency spec with no tracker link is **unresolvable** → surfaced as a warning naming the dep spec id, never silently dropped.
- **Relation projection (normalized, transport-blind).** For each resolved (current-issue, dep-issue) pair, ensure a **blocked-by** relation exists (current issue blocked by dep issue). Driven through a new normalized transport pair on the adapter interface — `setIssueRelation(issue, blockedBy)` + `listIssueRelations(issue)` — that both adapters implement, with **read-before-write** dedup (neither platform reliably no-ops a duplicate):
  - **Linear adapter:** MCP rung uses `save_issue` `blockedBy`/`blocks` **IF the pinned MCP schema exposes them** (re-verify at impl time — fn-64.3; the schema drifts). If MCP lacks relation params, fall back to the GraphQL rung when `LINEAR_API_KEY` is present, else `noop` receipt. GraphQL rung: `issueRelationCreate(input:{issueId, relatedIssueId, type: blocks})` — "A blocked by B" is a `blocks` edge with `issueId:B, relatedIssueId:A`. Dedup must query **both** `relations` AND `inverseRelations` (each with an explicit `first:` arg — Linear rejects connections without it) and canonicalize each edge to one direction before comparing.
  - **GitHub adapter:** prefer GitHub's **native issue dependencies** (GA 2025-08-21 — re-verify endpoint shape against official REST docs / a live `gh api` probe before coding, fn-64.4) via the REST `…/issues/{n}/dependencies/blocked_by` endpoints (`issue_id` is the numeric DB id, not `#N`; only `blocked_by` is writable; max 50/type). Feature-detect with a `GET` probe; **fall back to a provenance-fenced "Blocked by" body block** (`<!-- flow:deps -->`…`<!-- /flow:deps -->` list of `#N` references) when native deps are unavailable.
- **GitHub fenced-block ↔ body-merge ownership (CRITICAL).** The fenced `<!-- flow:deps -->` block is **flow-owned**: the body-merge layer (`references/body-merge.md`) MUST exclude that fenced region from divergence detection — exactly as flow provenance markers are already skipped — so a reconcile never folds flow's own dependency block back into the spec, and render never overwrites it. fn-64.4 owns the block *writer*; fn-64.5 + body-merge own the *exclusion rule*. **Concretely: define a canonical *tracker-body-for-merge* transform** — strip the fenced block before ALL hash / merge-base / divergence comparisons (`baseHashTracker`, `mergeBaseTracker`, and the `fetchIssue.body` fed to the comparison), and reinject/preserve it only when writing the GitHub issue body. Raw full-body hashing would still flag the block as tracker divergence and break echo-suppression — the strip must happen at the hash boundary, not just visually.
- **Provenance marking (flow-side).** Neither platform stores relation authorship, so tracker-sync records the edge keys it created in the `depRelations` ledger (mirroring the merge-base hash-provenance shape, NOT its paired-snapshot constraint). A relation not in the ledger / outside the fenced block is **never removed**.
- **Completed-blocker semantics.** A dependency whose local dep spec is `done` (→ its issue Done/Closed) is a **historical/completed blocker**: the relation stays visible on the tracker but must NOT feed back into Flow `ready=true` gating (readiness already treats done deps as satisfied — this hook must not regress that).

## API Contracts

- **flowctl plumbing** (deterministic, transport-blind, plugs into the existing `sync` subparser + ID canonicalizer): `flowctl sync list-dep-relations <spec-id> --json` → `[{dep_spec, dep_tracker_id, dep_identifier, dep_status(local spec status), projected: bool}]`; `flowctl sync set-dep-relation` / `clear-dep-relation` take the `depRelations[]` entry shape above and write atomically via `_write_sync_state`. Idempotent append mirrors `cmd_spec_add_dep` (dedup no-op). **Identifier widening lives here:** the flowctl tracker-identifier validator must accept bare `N` (numeric) in addition to `#N` / `owner/repo#N`, with tests — otherwise `sync set-tracker-id --identifier 42` fails before any adapter runs.
- **Adapter transport contract** (added to `references/adapter-interface.md`): normalized `setIssueRelation(issue, blockedBy)` + `listIssueRelations(issue) -> [{from, to, type, source}]`, implemented by BOTH adapters. Idempotency: read-before-write. `source` distinguishes ours-vs-theirs where the transport can; otherwise the flow-side ledger is authoritative.
- **Receipts (use the real enum):** receipt status is one of `{pushed,pulled,merged,updated,diverged,queued,errored,noop}`. A no-transport / bottom-rung projection writes a `noop` receipt; a surfaced conflict goes through `sync defer` and writes a `queued` receipt. There is no "deferred" status.
- **Warning surface:** missing tracker link on a dependency spec → a warning line naming the dependency spec id (and the parent spec), in the skill report and on the `sync receipt` (fn-57 `operation … event …` grammar).

## Edge Cases & Constraints

- **Idempotent rerun:** re-running over an already-projected dependency creates zero new relations / appends nothing to the GitHub fenced block (read-before-write + the provenance ledger / marker).
- **Missing dependency link:** dep spec not linked to any issue → warning naming the dep spec id; the rest of the sync proceeds (item-level failure isolation).
- **Completed dependency:** local dep spec `done` → relation remains visible as a completed blocker but does not block `ready=true` handling.
- **Manual relations preserved:** a relation tracker-sync cannot prove it created (not in the ledger / outside the fenced block) is never removed — on either adapter.
- **Self-edge:** never project a relation from an issue to itself — skip with a warning.
- **Cycle:** tolerate a dependency cycle in the flow graph — project each declared `depends_on_epics` edge as an independent direct relation, NO graph traversal / transitive expansion.
- **Collision (who-wins):** an edge present in `depRelations` AND still in Flow's `depends_on_epics`, but **missing remotely** (a tracker user removed the projected relation) → the collision case is evaluated **before** per-side rules; emit `sync defer` + a `queued` receipt and do NOT silently recreate the relation without confirmation. Re-creating a human-removed relation is the explicit anti-behavior.
- **Transport unavailable / reduced-fidelity:** no transport reachable → projection skipped with a `noop` receipt, never blocking the lifecycle; GitHub without native deps → fenced-block fallback, not a hard failure.
- **Cross-adapter consistency:** the normalized hook behaves identically from the skill's view regardless of adapter; only fidelity differs.

## Acceptance Criteria

- **R1:** A Flow spec with `depends_on_epics` whose dependency specs are linked to tracker issues creates matching **blocked-by** relations (current issue blocked by each dependency issue) on sync — verified on the **Linear** adapter (native relations, MCP-if-available else GraphQL rung).
- **R2:** The same projection works on the **GitHub** adapter — native REST issue dependencies where available, else a provenance-fenced "Blocked by" block of `#N` references in the issue body.
- **R3:** Re-running tracker-sync is idempotent on both adapters — no duplicate relations (read-before-write, canonicalized Linear edge compare across `relations`+`inverseRelations`), no duplicated fenced-block entries.
- **R4:** A dependency spec with no tracker link is surfaced as a warning that names the dependency spec id; the sync otherwise completes.
- **R5:** A `done` dependency remains visible as a completed blocker relation but does NOT block `ready=true` handling for the dependent spec.
- **R6:** Existing tracker relations that tracker-sync cannot prove it created are preserved (never removed) — on both adapters (ledger for native relations, fenced marker for the GitHub fallback).
- **R7:** Projection is provenance-tracked in flowctl sync state (`depRelations`, the entry shape above), written atomically; `flowctl sync list-dep-relations` enumerates edges + resolution + projected status; the flowctl identifier validator accepts bare `N`.
- **R8:** The relation hook is exposed through the normalized adapter interface (`setIssueRelation` / `listIssueRelations`) and is transport-blind in the skill — the skill code does not branch on Linear-vs-GitHub. Self-edges are skipped with a warning; cycles are projected as independent direct edges (no traversal).
- **R9:** Unit/integration coverage (pure-stdlib `unittest`, in-process handler calls asserting sidecar JSON, `test_tracker_sync_state.py` style) proves the flowctl plumbing: dep-relation add, idempotent rerun (no dup), missing-link warning, completed-blocker (local-`done`) status surfaced, self-edge skip, bare-`N` identifier acceptance, and the new sidecar field on a fresh spec.
- **R10:** The GitHub fenced-block ↔ body-merge ownership rule is implemented and tested (body-merge excludes the `<!-- flow:deps -->` region from divergence) AND the collision rule (ledgered edge missing remotely → `queued`/defer, no silent recreate) has explicit coverage.
- **R11:** Docs updated — `plugins/flow-next/docs/tracker-sync.md` (new Dependency-projection section parallel to Readiness projection), `docs/flowctl.md` (new subcommands), `references/adapter-interface.md`, `linear-graphql.md`, `linear-mcp.md`, `github.md`, `body-merge.md` (the exclusion rule), `steps.md`, SKILL.md; `GLOSSARY.md` (dependency projection, provenance ledger, completed-blocker rule); `CHANGELOG.md` + version bump via `scripts/bump.sh`; the Codex mirror regenerated via `scripts/sync-codex.sh`; and the flow-next.dev tracker-sync page + changelog updated in the same workstream.

## Boundaries

- **No new dependency authoring** — this projects existing `depends_on_epics` edges; it does not add a way to declare deps from the tracker side (tracker→flow dep ingestion is out of scope).
- **No stale-relation deletion beyond the provenance-safe case** — if a `depends_on_epics` edge is removed from a spec, cleaning up the now-stale projected relation is a follow-up; R6 only mandates we never remove non-ours. Removing ours-but-stale is optional/best-effort.
- **No readiness-model changes** — `ready=true` gating already treats done deps as satisfied; this spec must not alter that, only avoid regressing it.
- **No transitive/graph expansion** — only direct `depends_on_epics` edges are projected.
- **GitHub Projects fields** (status columns, custom dependency fields) are out of scope — issue-level dependencies / body-block only.
- **Tracker is a projection, never a control plane** — projected relations never override `depends_on_epics`; flow stays authoritative.

## Decision Context

This belongs in tracker-sync, not per-repo workaround logic, because the dependency graph is a first-class Flow artifact and the bridge's whole job is projection (body, status, comments already sync two-way — relations are the missing edge type). SapienXT hand-added relations as a stopgap; that doesn't scale and drifts the moment the flow graph changes.

**Both adapters, one hook.** The original issue framed this as Linear-only; Gordon extended it to GitHub too. The right shape is a single transport-blind relation hook on the adapter interface, implemented at each adapter's native fidelity — Linear has first-class issue relations; GitHub has native issue dependencies (GA Aug 2025) and a body-block fallback for older/unsupported repos. Keeping the skill transport-blind (R8) means the dependency logic lives once and both trackers inherit it.

**blocked-by is the right direction:** Flow's `depends_on_epics` means "this spec depends on / is blocked by those" — on Linear a `blocks` edge with the operands swapped; on GitHub a `blocked_by` dependency.

**Provenance over diff-reconcile:** neither platform records who created a relation, so we only ever touch relations we can prove we created (flow-side `depRelations` ledger for native, fenced marker for the GitHub fallback). Wrongly deleting a human's manual relation is high-cost and silent, so we stay conservative — mirroring the bridge's existing "surface diffs, never overwrite" posture, including the collision rule (a human-removed relation is never silently recreated).

**Completed-blocker handling** is explicit because naive projection (drop the relation once the dep is done) would erase real historical ordering from the board; keeping it visible while not re-gating readiness preserves both the audit trail and the existing readiness semantics.

## Requirement coverage

| R-ID | Task |
|---|---|
| R7, R9 | fn-64.1 — flowctl `depRelations` state + entry shape + `list/set/clear-dep-relation` + bare-`N` identifier widening + unit tests |
| R8 | fn-64.2 — adapter-interface contract: `setIssueRelation` / `listIssueRelations` + relation struct + direction convention |
| R1, R3 | fn-64.3 — Linear adapter relation transport (MCP `save_issue` w/ schema re-verify + GraphQL `issueRelationCreate`, read-before-write dedup across relations+inverseRelations) |
| R2, R3 | fn-64.4 — GitHub adapter relation transport (native REST deps w/ live-probe verify + fenced body-block writer, DB-id resolution) |
| R3, R4, R5, R6, R8, R10 | fn-64.5 — `projectDepRelations` transport-blind skill hook (push+reconcile, warnings, completed-blocker, never-clobber, collision→queued/defer, self/cycle, body-merge exclusion) |
| R11 | fn-64.6 — docs + GLOSSARY + CHANGELOG + version bump + codex mirror regen + flow-next.dev |


$ git status
On branch fn-83-work-loop-speed-conservative-plan-sync
You are in a sparse checkout with 100% of tracked files present.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   .flow/specs/fn-83-work-loop-speed-conservative-plan-sync.json
	modified:   .flow/specs/fn-83-work-loop-speed-conservative-plan-sync.md
	modified:   .flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.4.json
	modified:   .flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.4.md
	modified:   plugins/flow-next/scripts/flowctl.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	.flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.6.json
	.flow/tasks/fn-83-work-loop-speed-conservative-plan-sync.6.md
	optimization/worker-anchor/
	plugins/flow-next/tests/test_anchor_bundle.py

no changes added to commit (use "git add" and/or "git commit -a")

$ git log -5 --oneline
7d628564 chore(flow): close fn-83.2 — done summary + evidence
c0477c32 feat(eval): plan-sync gate corpus — frozen real-agent answer key + zero-false-skip CI check (fn-83.2)
43264e13 chore(flow): close fn-83.1 — done summary + evidence
5993c446 feat(flowctl): plan-sync-probe — fail-open drift lattice, planSync.gate config, gate ledger
23ab917d chore(flow): plan fn-83 (5 tasks, plan-review SHIP r3) + FLOW-29 link

$ flowctl config get memory.enabled --json
{
  "success": true,
  "key": "memory.enabled",
  "value": true
}

$ flowctl memory list --json
{
  "success": true,
  "entries": [
    {
      "entry_id": "bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18",
      "title": "Abort-option copy must reflect pre-prompt state mutations (idempotent != no chan",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-setup/workflow.md",
      "tags": [
        "fn-45",
        "abort-option",
        "setup-skill",
        "copy-drift",
        "codex-review",
        "user-consent"
      ],
      "date": "2026-05-18",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18.md"
    },
    {
      "entry_id": "bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27",
      "title": "Backlog SELECT must not drop a dep-blocked item to NO_WORK \u2014 it routes to BLOCKE",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-pilot/references/backlog-mode.md",
      "tags": [
        "fn-68",
        "pilot",
        "backlog-mode",
        "skill-authoring",
        "select-vs-triage",
        "terminal-grammar",
        "rp-review",
        "review-feedback"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05",
      "title": "Codex mirror audit must verify R2 block lands before a COMPLETE sentence, not ju",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-qa/references/qa-discipline.md",
      "tags": [
        "sync-codex",
        "codex",
        "mirror",
        "fn-53",
        "AskUserQuestion",
        "plain-text-numbered-prompt",
        "mid-sentence-injection",
        "multi-line-ask",
        "tool-rewrites",
        "audit",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/codex-mirror-audit-must-verify-r2-block-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18",
      "title": "Codex mirror smoke docs miss composed transform output (abort + Other)",
      "track": "bug",
      "category": "build-errors",
      "module": "agent_docs/local-dev.md",
      "tags": [
        "sync-codex",
        "codex",
        "mirror",
        "fn-45",
        "smoke-docs",
        "AskUserQuestion",
        "abort-option"
      ],
      "date": "2026-05-18",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18.md"
    },
    {
      "entry_id": "bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08",
      "title": "detect/validate must require SPECS_DIR even when EPICS_DIR present",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-43",
        "rename",
        "detect",
        "validate",
        "write-location",
        "backward-compat",
        "deprecation",
        "env-vars",
        "acceptance-criteria",
        "review-feedback"
      ],
      "date": "2026-05-08",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08.md"
    },
    {
      "entry_id": "bug/build-errors/docs-activation-command-for-string-enum-2026-06-05",
      "title": "Docs activation command for string-enum config knob used bool true instead of th",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/docs/flowctl.md, .flow/usage.md",
      "tags": [
        "fn-55",
        "work.delegate",
        "config-enum",
        "docs-drift",
        "activation-predicate",
        "codex-delegation",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/docs-activation-command-for-string-enum-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12",
      "title": "Embedded self-check greps in reference docs need POSIX classes + whitespace tole",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/references/html-artifacts.md",
      "tags": [
        "fn-62",
        "reference-doc",
        "grep",
        "portability",
        "bsd-grep",
        "self-check",
        "copy-paste-blocks",
        "review-feedback"
      ],
      "date": "2026-06-12",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12.md"
    },
    {
      "entry_id": "bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04",
      "title": "Env-marker gate must scan the namespace, not a fixed var list",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-work/references/codex-delegation.md",
      "tags": [
        "fn-55",
        "skill-prose-gate",
        "env-markers",
        "opencode",
        "platform-gate",
        "codex-delegation"
      ],
      "date": "2026-06-04",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04.md"
    },
    {
      "entry_id": "bug/build-errors/fn-44-review-cycle-lessons-2026-05-21",
      "title": "fn-44 review-cycle lessons (10+ NEEDS_WORK rounds across 4 tasks)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-interview, plugins/flow-next/skills/flow-next-capture, plugins/flow-next/scripts/flowctl.py, scripts/sync-codex.sh, plugins/flow-next/templates/spec.md",
      "tags": [
        "fn-44",
        "scope-flag",
        "impl-review",
        "codex-review",
        "json-contract",
        "html-comments",
        "r17-cross-link",
        "r21-drift-guard",
        "merge-contract",
        "auxiliary-sections",
        "scoped-diff",
        "relative-paths",
        "codex-mirror"
      ],
      "date": "2026-05-21",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/fn-44-review-cycle-lessons-2026-05-21.md"
    },
    {
      "entry_id": "bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03",
      "title": "Id-grammar widening must cover the FULL command surface, not just named commands",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "id-resolution",
        "canonicalizer",
        "enumeration",
        "impl-review",
        "case-rule",
        "validator-separation",
        "sync-receipt",
        "sync-defer",
        "final-integration",
        "merge-base"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03.md"
    },
    {
      "entry_id": "bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12",
      "title": "Lavish interactive-only gate must check MODE var AND env markers in-snippet",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-capture/workflow.md",
      "tags": [
        "fn-62",
        "lavish",
        "skill-authoring",
        "safety-gates",
        "review-feedback",
        "html-artifacts"
      ],
      "date": "2026-06-12",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12.md"
    },
    {
      "entry_id": "bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11",
      "title": "Mirror regen exposes latent canonical gaps: path rewrites, .flow persistence, di",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-60",
        "sync-codex",
        "codex-mirror",
        "land",
        "flow-persistence",
        "tracker-dispatch",
        "ledger",
        "review-feedback",
        "release"
      ],
      "date": "2026-06-11",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11.md"
    },
    {
      "entry_id": "bug/build-errors/optional-side-effect-snippets-need-2026-06-12",
      "title": "Optional side-effect snippets need guarded git steps; check-ignore the exact fil",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-make-pr/workflow.md",
      "tags": [
        "fn-62",
        "make-pr",
        "html-artifacts",
        "skill-authoring",
        "set-e",
        "check-ignore",
        "review-feedback"
      ],
      "date": "2026-06-12",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/optional-side-effect-snippets-need-2026-06-12.md"
    },
    {
      "entry_id": "bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18",
      "title": "Policy-claim inversion: sweep ALL surfaces (both ceremony copies, docs, CLI head",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "fn-66",
        "tracker-sync",
        "ceremony-duplicate",
        "dispatch-grammar",
        "docs-parity",
        "steps.md",
        "SKILL.md"
      ],
      "date": "2026-06-18",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18.md"
    },
    {
      "entry_id": "bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27",
      "title": "R2 ask-block mis-injected into negation-only autonomy prose on mirror regen",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-pilot, plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "fn-68",
        "sync-codex",
        "codex-mirror",
        "pilot",
        "backlog-mode",
        "tracker-sync",
        "AskUserQuestion",
        "R2-injection",
        "is_negative_context",
        "autonomy",
        "review-feedback"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10",
      "title": "R2 ask-block must never anchor in autonomous hard-error prose; mode-rename sweep",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-make-pr/workflow.md",
      "tags": [
        "fn-59",
        "sync-codex",
        "codex-mirror",
        "R2-injection",
        "is_negative_context",
        "autonomous",
        "FLOW_AUTONOMOUS",
        "make-pr",
        "review-feedback"
      ],
      "date": "2026-06-10",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/r2-ask-block-must-never-anchor-in-2026-06-10.md"
    },
    {
      "entry_id": "bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26",
      "title": "Scout fallback prose drifted from spec's decision-lock command shape",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/agents/context-scout.md",
      "tags": [
        "fn-50",
        "clawpatch",
        "scouts",
        "decision-lock-in",
        "flag-drift",
        "codex-review"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26.md"
    },
    {
      "entry_id": "bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05",
      "title": "sed-piped default masks empty source: || fallback never fires",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-qa/workflow.md",
      "tags": [
        "fn-53",
        "skill-bash",
        "base-ref-detection",
        "branch-match",
        "sed-exit-code",
        "make-pr-pattern",
        "codex-review"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05",
      "title": "Skill-adding version bump leaves stale skill/command counts in JSON manifest des",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/flow-next/.codex-plugin/plugin.json",
      "tags": [
        "fn-53",
        "version-bump",
        "bump.sh",
        "skill-count",
        "manifest",
        "marketplace",
        "codex-mirror",
        "docs-drift",
        "release"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05.md"
    },
    {
      "entry_id": "bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26",
      "title": "Skill bash `set -- $ARGUMENTS` can't honor 'verbatim' passthrough",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-map/workflow.md",
      "tags": [
        "fn-50",
        "skill-bash",
        "argument-parsing",
        "set-minus-f",
        "codex-review",
        "passthrough",
        "clawpatch-wrap"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26.md"
    },
    {
      "entry_id": "bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10",
      "title": "Skill prose must match real flowctl surfaces (fields, status enums, subcommands)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-pilot/workflow.md",
      "tags": [
        "fn-59",
        "pilot",
        "skill-authoring",
        "flowctl-json",
        "task-status",
        "rp-review",
        "fn-68",
        "backlog-mode",
        "safety-gates",
        "dry-run",
        "review-feedback",
        "fn-82",
        "skill-prose",
        "dedupe",
        "progressive-disclosure"
      ],
      "date": "2026-06-10",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-prose-must-match-real-flowctl-2026-06-10.md"
    },
    {
      "entry_id": "bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11",
      "title": "Skill workflow snippets must enforce what the prose mandates (vars, gates, dispa",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-60",
        "land",
        "skill-authoring",
        "codex-review",
        "safety-gates",
        "review-feedback"
      ],
      "date": "2026-06-11",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11.md"
    },
    {
      "entry_id": "bug/build-errors/status-policy-map-needs-a-matching-2026-06-18",
      "title": "Status-policy map needs a matching reconcile-loop branch per rung (map \u2260 write)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md",
      "tags": [
        "fn-66",
        "tracker-sync",
        "status",
        "reconcile",
        "who-wins",
        "in-review",
        "merge-evidence",
        "rp-review"
      ],
      "date": "2026-06-18",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/status-policy-map-needs-a-matching-2026-06-18.md"
    },
    {
      "entry_id": "bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18",
      "title": "sync-codex.sh tool-substitution needs prose surgery + context-aware injection",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh",
      "tags": [
        "sync-codex",
        "codex",
        "mirror",
        "fn-45",
        "AskUserQuestion",
        "tool-rewrites",
        "injection",
        "markdown-tables",
        "fenced-code-blocks",
        "fn-50",
        "FLOWCTL",
        "prelude",
        "agents",
        "scouts",
        "symmetry-gap",
        "R2-injection",
        "is_negative_context",
        "fn-55",
        "plain-text-numbered-prompt",
        "reference-doc"
      ],
      "date": "2026-05-18",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/sync-codexsh-tool-substitution-needs-2026-05-18.md"
    },
    {
      "entry_id": "bug/build-errors/template-rewrite-env-var-cascade-2026-05-09",
      "title": "Env-var cascade in templates + canonical config.env knob alignment",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-ralph-init/templates, config.env, ralph.sh",
      "tags": [
        "template",
        "ralph",
        "config-env",
        "env-var-cascade",
        "review-feedback"
      ],
      "date": "2026-05-09",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/build-errors/template-rewrite-env-var-cascade-2026-05-09.md"
    },
    {
      "entry_id": "bug/test-failures/archaeology-fn-strip-can-over-strip-a-2026-07-02",
      "title": "Archaeology fn-strip can over-strip a test-pinned canonical breadcrumb",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "fn-82",
        "archaeology",
        "fn-strip",
        "sync-codex",
        "mirror",
        "test-pinned",
        "allowlist",
        "final-gate"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/archaeology-fn-strip-can-over-strip-a-2026-07-02.md"
    },
    {
      "entry_id": "bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02",
      "title": "Final-gate grep for a forbidden token hits the prohibition prose that bans it",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/skills/flow-next-impl-review",
      "tags": [
        "acceptance-gates",
        "grep",
        "spec-authoring",
        "fn-81",
        "review-feedback",
        "rp-slices"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02.md"
    },
    {
      "entry_id": "bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09",
      "title": "Smoke discipline: variable-form CLI, hermetic env, line-level guard scope",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/scripts",
      "tags": [
        "smoke",
        "env-hermeticity",
        "variable-form-cli",
        "line-level-guard",
        "review-feedback"
      ],
      "date": "2026-05-09",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09.md"
    },
    {
      "entry_id": "bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26",
      "title": "Test fixtures must mirror upstream Zod enum, not concept",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/fixtures/clawpatch-map, plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-50",
        "clawpatch",
        "zod-schema",
        "fixture-drift",
        "confidence-enum",
        "codex-review",
        "duck-typing"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26.md"
    },
    {
      "entry_id": "bug/test-failures/test-production-path-not-parallel-construction-2026-05-21",
      "title": "Test the production path, not a parallel construction",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests, plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "testing",
        "production-form",
        "mock-patch",
        "argparse-two-token",
        "routing-table",
        "dual-emit",
        "review-feedback"
      ],
      "date": "2026-05-21",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/test-failures/test-production-path-not-parallel-construction-2026-05-21.md"
    },
    {
      "entry_id": "bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27",
      "title": "flowctl on-disk per-key counter: count by stored key + lock + coerce sort",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-68",
        "pilot-log",
        "tick-counter",
        "race-condition",
        "flock",
        "rp-review",
        "review-feedback"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27.md"
    },
    {
      "entry_id": "bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03",
      "title": "Who-wins ladder must check the collision case before single-field rules",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md",
      "tags": [
        "fn-52",
        "tracker-sync",
        "who-wins",
        "status",
        "deadlock",
        "conflictTiebreak",
        "ordering",
        "impl-review"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03.md"
    },
    {
      "entry_id": "bug/performance/linear-graphql-every-nodes-connection-2026-06-03",
      "title": "Linear GraphQL: every {nodes} connection needs first: \u2014 incl. workflowStates/tea",
      "track": "bug",
      "category": "performance",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/linear-graphql.md",
      "tags": [
        "fn-52",
        "tracker-sync",
        "linear",
        "graphql",
        "rate-limit",
        "complexity",
        "connection",
        "first",
        "impl-review"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/performance/linear-graphql-every-nodes-connection-2026-06-03.md"
    },
    {
      "entry_id": "bug/security/rollback-path-sanitizer-must-not-2026-06-05",
      "title": "Rollback path-sanitizer must not trim/rewrite bytes; guard git clean against emp",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-55",
        "codex-delegation",
        "rollback",
        "git-clean",
        "path-sanitization",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/security/rollback-path-sanitizer-must-not-2026-06-05.md"
    },
    {
      "entry_id": "bug/security/shell-command-allowlist-gates-must-2026-06-05",
      "title": "Shell-command allowlist gates must tokenize argv, not substring-match",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/hooks/ralph-guard.py",
      "tags": [
        "fn-55",
        "ralph-guard",
        "codex-delegation",
        "shlex",
        "allowlist",
        "bypass",
        "security",
        "review-feedback"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/security/shell-command-allowlist-gates-must-2026-06-05.md"
    },
    {
      "entry_id": "bug/integration/adding-a-review-backend-sweep-all-2026-06-29",
      "title": "Adding a review backend: sweep ALL enumeration sites (config table, stage list, ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/docs, plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review-backend",
        "enumeration-drift",
        "docs-sweep",
        "cursor",
        "fn-74"
      ],
      "date": "2026-06-29",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/adding-a-review-backend-sweep-all-2026-06-29.md"
    },
    {
      "entry_id": "bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28",
      "title": "Adding a tracker to tracker-sync: sweep WHOLE tree + read adapter ref for dep-pr",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync",
      "tags": [
        "tracker-sync",
        "gitlab",
        "fn-69",
        "doc-sweep",
        "flow:deps",
        "dependency-projection",
        "impl-review",
        "jira",
        "fn-70",
        "per-adapter-fidelity",
        "adapter-ref-crosscheck"
      ],
      "date": "2026-06-28",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/adding-a-tracker-to-tracker-sync-sweep-2026-06-28.md"
    },
    {
      "entry_id": "bug/integration/byte-for-byte-spec-contract-branch-2026-07-01",
      "title": "Byte-for-byte spec contract: branch prose into variants, don't annotate shared l",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-plan-review/SKILL.md",
      "tags": [
        "fn-78",
        "skill-prose",
        "review-feedback",
        "rp-eligibility",
        "byte-for-byte"
      ],
      "date": "2026-07-01",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/byte-for-byte-spec-contract-branch-2026-07-01.md"
    },
    {
      "entry_id": "bug/integration/ceremony-validation-must-read-persisted-2026-06-28",
      "title": "Ceremony validation must read PERSISTED config, not re-race env; don't collapse ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/steps.md",
      "tags": [
        "tracker-sync",
        "jira",
        "fn-70",
        "discovery-ceremony",
        "readyState",
        "persisted-config",
        "authScheme",
        "rp-review"
      ],
      "date": "2026-06-28",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/ceremony-validation-must-read-persisted-2026-06-28.md"
    },
    {
      "entry_id": "bug/integration/drop-receipt-to-break-codex-2026-05-09",
      "title": "Drop receipt to break codex confabulation in long review fix loops",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review",
        "codex",
        "confabulation",
        "receipt",
        "fn-43"
      ],
      "date": "2026-05-09",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/drop-receipt-to-break-codex-2026-05-09.md"
    },
    {
      "entry_id": "bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17",
      "title": "gh api -f stringifies numeric body fields (issue_id) \u2192 GitHub 422; use -F",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/github.md",
      "tags": [
        "fn-64",
        "tracker-sync",
        "github",
        "gh-api",
        "rest",
        "422",
        "issue-dependencies"
      ],
      "date": "2026-06-17",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17.md"
    },
    {
      "entry_id": "bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05",
      "title": "Heredoc-built JSON breaks on free-form interpolated values",
      "track": "bug",
      "category": "integration",
      "module": "skills/flow-next-qa/workflow.md",
      "tags": [
        "json",
        "shell",
        "receipt",
        "escaping",
        "skill-authoring"
      ],
      "date": "2026-06-05",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05.md"
    },
    {
      "entry_id": "bug/integration/markerstruct-field-semantics-must-2026-06-27",
      "title": "Marker/struct-field semantics must update the PRODUCER adapter contract, not jus",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md",
      "tags": [
        "fn-68",
        "tracker-sync",
        "adapter-interface",
        "marker",
        "comments-sync",
        "listComments",
        "question-valve",
        "nine-method",
        "cross-model-review"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/markerstruct-field-semantics-must-2026-06-27.md"
    },
    {
      "entry_id": "bug/integration/rp-builder-file-slices-cause-false-2026-06-10",
      "title": "RP builder file slices cause false-positive 'missing docs' review findings",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-impl-review",
      "tags": [
        "rp",
        "impl-review",
        "builder-slices",
        "false-positive",
        "select-get",
        "review-feedback"
      ],
      "date": "2026-06-10",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/rp-builder-file-slices-cause-false-2026-06-10.md"
    },
    {
      "entry_id": "bug/integration/set-tracker-id-rejected-github-n-2026-06-03",
      "title": "set-tracker-id rejected GitHub",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "github",
        "identifier",
        "validator",
        "smoke-test"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md"
    },
    {
      "entry_id": "bug/integration/skill-bash-blocks-re-declare-every-2026-07-02",
      "title": "Skill bash blocks: re-declare EVERY literal path per block (vars die across tool",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills",
      "tags": [
        "path-persistence",
        "skill-authoring",
        "rp-review",
        "fn-81"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/skill-bash-blocks-re-declare-every-2026-07-02.md"
    },
    {
      "entry_id": "bug/integration/trackers-auto-linkify-issue-key-2026-06-03",
      "title": "Trackers auto-linkify issue-key substrings inside markers (even in HTML comments",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md",
      "tags": [
        "fn-52",
        "tracker-sync",
        "linear",
        "marker",
        "dedup",
        "linkify",
        "smoke-test"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/integration/trackers-auto-linkify-issue-key-2026-06-03.md"
    },
    {
      "entry_id": "bug/data/fence-preserving-writer-needs-fence-2026-07-02",
      "title": "Fence-preserving writer needs fence-aware readers/validators (write/read parity)",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-79",
        "task-sections",
        "fenced-code",
        "markdown-parsing",
        "cursor-review"
      ],
      "date": "2026-07-02",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/data/fence-preserving-writer-needs-fence-2026-07-02.md"
    },
    {
      "entry_id": "bug/data/migrationrollback-cli-10-review-cycle-2026-05-08",
      "title": "Migration/rollback CLI: 10 review-cycle pitfalls (fn-43.3)",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-43",
        "migration",
        "rollback",
        "lockfile",
        "sentinel",
        "atomic-write",
        "crash-recovery",
        "cross-platform",
        "review-feedback"
      ],
      "date": "2026-05-08",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/data/migrationrollback-cli-10-review-cycle-2026-05-08.md"
    },
    {
      "entry_id": "bug/data/paired-snapshot-setter-must-write-both-2026-06-03",
      "title": "Paired-snapshot setter must write both halves atomically (merge base)",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-52",
        "tracker-sync",
        "merge-base",
        "3-way-merge",
        "invariant",
        "setter",
        "impl-review"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/data/paired-snapshot-setter-must-write-both-2026-06-03.md"
    },
    {
      "entry_id": "bug/ui/flow-nextdev-docs-page-needs-2026-06-03",
      "title": "flow-next.dev docs page needs registering in BOTH astro sidebar + site.ts navGro",
      "track": "bug",
      "category": "ui",
      "module": "src/lib/site.ts",
      "tags": [
        "flow-next.dev",
        "docs-site",
        "starlight",
        "navigation",
        "navGroups",
        "DocsRail",
        "fn-52"
      ],
      "date": "2026-06-03",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/bug/ui/flow-nextdev-docs-page-needs-2026-06-03.md"
    },
    {
      "entry_id": "knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30",
      "title": "Audit sync-codex.sh during planning for Codex mirror impact",
      "track": "knowledge",
      "category": "workflow",
      "module": "planning",
      "tags": [
        "sync-codex",
        "codex",
        "planning",
        "mirror",
        "validation",
        "subagents",
        "tool-rewrites",
        "openai-yaml"
      ],
      "date": "2026-04-30",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30.md"
    },
    {
      "entry_id": "knowledge/workflow/final-integration-tasks-need-wider-impl-2026-05-26",
      "title": "Final-integration tasks need wider impl-review base",
      "track": "knowledge",
      "category": "workflow",
      "module": "review",
      "tags": [
        "fn-50",
        "impl-review",
        "review-scope",
        "final-task",
        "multi-task-spec",
        "base-commit",
        "merge-base",
        "codex"
      ],
      "date": "2026-05-26",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/workflow/final-integration-tasks-need-wider-impl-2026-05-26.md"
    },
    {
      "entry_id": "knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25",
      "title": "Factory Droid platform status \u2014 2026-05",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/docs/platforms.md",
      "tags": [
        "droid",
        "factory-ai",
        "cross-platform",
        "fn-48",
        "interop",
        "plugin-root",
        "hooks",
        "Execute"
      ],
      "date": "2026-05-25",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md"
    },
    {
      "entry_id": "knowledge/decisions/tracker-sync-is-projection-not-2026-06-01",
      "title": "Tracker sync is projection, not coordination (Linear-first)",
      "track": "knowledge",
      "category": "decisions",
      "module": "strategy",
      "tags": [
        "strategy-override",
        "tracker-sync",
        "linear"
      ],
      "date": "2026-06-01",
      "status": "active",
      "path": "/Users/gordon/work/flow-next/.flow/memory/knowledge/decisions/tracker-sync-is-projection-not-2026-06-01.md"
    }
  ],
  "legacy": [],
  "count": 55,
  "status": "active"
}

$ flowctl glossary list --json
{
  "success": true,
  "groups": [
    {
      "path": "/Users/gordon/work/flow-next/GLOSSARY.md",
      "entries": [
        {
          "term": "Spec",
          "definition": "The central artefact of flow-next: a specification at `.flow/specs/<id>.md` (markdown body) plus `.flow/specs/<id>.json` (metadata sidecar, post-1.0). Reviewable on its own; cross-model-reviewed; verifiable against prior handovers; frozen at handover. Replaces the term *epic* from the 0.x line.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Ready",
          "definition": "A human-owned boolean on the spec record (default `false`, toggled via `flowctl spec ready` / `spec unready`) marking a spec complete enough to hand to an agent \u2014 the entry gate autonomous loops consume. Orthogonal to `status` (`open|done`): a ready spec stays `open` through planning and work. Human-owned or tracker-projected (`tracker.readyState` pulls the configured tracker state onto the local flag, one-way), never agent-inferred. Opt-in and invisible until adopted: the flag is written lazily, non-adopters see no badge, prompts, or warnings anywhere.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Task",
          "definition": "An execution unit under a spec, sized to fit one `/flow-next:work` iteration (~100k tokens fresh context). Tasks declare dependencies (`requires:`) and may declare which spec acceptance criteria they advance (`satisfies: [R1, R3]`). Implemented by a worker subagent with re-anchored context.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "R-ID",
          "definition": "A numbered acceptance criterion in a spec, format `**R1:** ...`, `**R2:** ...`. Renumber-forbidden after the first review cycle: deletions leave gaps, new criteria take the next unused number. R-IDs are the load-bearing identity of a requirement across the spec, the tasks that satisfy it, the commits that reference it, and the PR body coverage table.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Handover object",
          "definition": "A named, reviewable artefact that carries context across a step in the agentic SDLC. flow-next defines six handover states: the spec at business-layer completion (#1) and at full completion (#2) \u2014 both the **same** `.flow/specs/<spec-id>.md` file at successive layers, NOT two separate specs \u2014 then the implementation plan (#3), the working implementation (#4), the cross-model code review (#5), and the PR-as-cognitive-aid (#6). Each is reviewable on its own, cross-model-verified, and frozen at handover. The chain of handovers replaces the standups / refinement / design-review touchpoints that pre-agentic Agile relied on.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Re-anchoring",
          "definition": "Re-reading the spec, the task, and `git log` since branch base before each task starts. Counters context drift in long-running agent sessions per Anthropic guidance. Worker subagents re-anchor on every iteration; `/flow-next:work` re-anchors every loop turn.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Cross-model review",
          "definition": "A different model reviews the artefact produced by the first model. Applied at every handover. Backends: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor `cursor-agent` CLI (cursor). The disagreement surface between writing model and reviewing model is where the gaps live.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Feature map",
          "definition": "The `.clawpatch/features/*.json` index produced by `clawpatch map` and consumed by flow-next scouts via `flowctl repo-map`. Semantic feature slices across ~20 languages/frameworks (Zod-validated upstream, `schemaVersion: 1`). Wrapped by the opt-in `/flow-next:map` skill; flow-next core (flowctl) never imports or requires clawpatch \u2014 when `.clawpatch/` is absent, scouts gracefully fall back to grep/glob.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "features_anchored",
          "definition": "Optional scout output field listing feature slices from the feature map that overlap the current scope. Emitted by `repo-scout` and `context-scout` when `.clawpatch/features/*.json` is present; omitted when absent. Each entry carries a `last_mapped` timestamp so downstream skills can flag staleness (informational signal, not a block).",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Receipt",
          "definition": "A JSON artefact that gates Ralph state transitions. `flowctl impl-review` writes a receipt at `.flow/review-receipts/<branch>.json` with verdict (`SHIP` / `NEEDS_WORK` / `MAJOR_RETHINK`), confidence anchors, introduced vs pre-existing finding counts, and the deferred / suppressed counts. Ralph reads receipts to decide loop progression.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Worker subagent",
          "definition": "A subagent dispatched by `/flow-next:work` to implement a single task with fresh context. Re-anchors the spec + task + git state, implements the task, records evidence (commits + tests + done summary), and exits. The fresh context per task is what enables N tasks to run in parallel without context-bleed.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Carmack-level review",
          "definition": "The strict cross-model review tier flow-next runs by default. References John Carmack review standard. Five confidence anchors (0/25/50/75/100) gate findings; `<75` suppressed except P0 @ 50+; introduced vs pre-existing classification means only introduced findings count toward the verdict.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Triage skip",
          "definition": "A deterministic whitelist pre-check that returns `SHIP` without invoking a review backend, for trivial diffs: lockfile-only / docs-only / release-chore / generated-file-only. `flowctl triage-skip` is the helper. On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "PR-as-cognitive-aid",
          "definition": "A structured PR body synthesizing nine flow-next state streams (spec with R-IDs, per-task done summary + evidence commits, decisions / bug / architecture-patterns memory, glossary changes, strategy alignment, deferred review findings, the diff itself) into a reviewable artefact. Body sections: TL;DR, R-ID coverage table, Critical changes, Decisions, Memory, Glossary/strategy deltas, Open items, Where to look. Produced by `/flow-next:make-pr`.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Ralph",
          "definition": "The flow-next hardened autonomous harness. External shell loop drives fresh Claude / Codex sessions per task with cross-model review gates, hook-enforced guardrails (ralph-guard / DCG), and receipt-based proof-of-work. Consumes **fully planned** specs only \u2014 it iterates plan-review -> work -> impl-review -> spec-completion-review until the spec ships or the iteration cap is hit; it never runs the planning fan-out (planning stays with the human or pilot). Differentiator from `ralph-wiggum`-style open-loop autonomous agents. The default autonomy path is the pilot + land pipeline; reach for Ralph when a run outlasts a session or prose guardrails aren't enough \u2014 Ralph owns the loop in a shell script, pilot hands the loop to the host's `/loop` / `/goal` primitives.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Pilot",
          "definition": "The single-tick build-loop conductor (`/flow-next:pilot`): one tick advances one ready spec by one pipeline stage (plan / plan-review / work / `[optional qa]` / make-pr \u2014 see [QA stage](#qa-stage-pipelineqa)) and ends with a terminal `PILOT_VERDICT` line; the host's `/loop` or `/goal` owns iteration. Signals autonomy to sub-skills via the `mode:autonomous` token + `FLOW_AUTONOMOUS=1` env (distinct from `FLOW_RALPH`; never activates ralph-guard). Selection consumes the fn-58 `ready` gate; two healthy no-advance ticks clear the spec's `ready` flag (don't-thrash). The default `ready` mode selects only already-ready specs; the opt-in [backlog mode](#backlog-mode-pilotautonomy) widens it to the whole open backlog.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Backlog mode (`pilot.autonomy`)",
          "definition": "Pilot's opt-in wide-autonomy behavior (fn-68), gated by config `pilot.autonomy \u2208 {ready (default), backlog}` (per-run override `--backlog` / `--auto`; with the gate off, pilot is byte-for-byte unchanged and `references/backlog-mode.md` is never even read). A backlog tick **enumerates the full open set** \u2014 flow specs (`flowctl ready --all`) **plus** tracker issues at the promoted lane (`listOpenIssues`, unioned in by the skill) \u2014 selects the top **dep-ordered** actionable item, runs the [triage stage](#triage-stage-backlog-mode) in front of pilot's existing pipeline, and either advances it one stage (`plan \u2192 plan-review \u2192 work \u2192 [qa] \u2192 make-pr`) or parks it behind an [async question](#ask-stage--question-valve). It is a **leftward extension of the same single-tick conductor**, not a new skill or altitude: one `/loop`/`/goal` target, one verdict grammar, one mental model; the host primitive still owns repetition. The consent boundary moves from *before* the loop to *inside the loop, on block* \u2014 but the load-bearing boundaries hold: it **never authors a spec** (a thin/missing spec is surfaced as a \"run `/flow-next:capture` or `/flow-next:interview`\" gap, never auto-written), **never sets the `ready` flag** (promotion is the human's board act), and **never merges** (land stays human-gated). Readiness is the human's **explicit signal** (the fn-58 ready gate set OR tracker status exactly at `tracker.readyState`), never an agent-inferred completeness score \u2014 un-promoted backlog items are skipped silently.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Triage stage (backlog mode)",
          "definition": "The classify-and-route stage backlog mode runs **in front of** pilot's existing `classify`, on the selected item only. It reads the spec **agentically** (the host's judgment, never a flowctl-computed `triageClass`) and routes by *explicit state first*: **workable** (ready signal + complete spec) \u2192 select-and-advance (pilot's existing path); **ready-but-thin / ready-but-ambiguous** (signal present, spec missing or too thin to act on) \u2192 [`ask`](#ask-stage--question-valve) (kick back with the gap, never build, never auto-author); **dep-unsatisfied** \u2192 `BLOCKED <id> by <dep>` (a state-changing surface of the dep wait); **needs a human decision** \u2192 `ask`. A *live* triage always lands on a **state-changing terminal** (`ADVANCED` / `ASKED` / `BLOCKED` / `NEEDS_HUMAN`) so an item can never re-select forever; `TRIAGED <id> <class>` is **diagnostic / `--dry-run` only**. `needs-spec` is always a *promoted* item missing a workable spec \u2014 never an un-promoted idea, which is simply skipped.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Ask stage / question valve",
          "definition": "Backlog mode's **async human-in-the-loop valve** \u2014 \"stuck\" becomes a question, not a stall, and never an interactive `AskUserQuestion`. When it cannot safely proceed, the `ask` stage writes each Open Question behind a **stable anchor** `<!-- flow-next:question id=<hash> status=open -->` (`id` hashes **stable fields only** \u2014 `subjectId` + blocked-stage + reason code + question slug; the free-prose reason is *outside* the hash so rephrasing never duplicates) and surfaces it where the item lives: a **spec-backed** item parks via the spec's `## Open Questions` section **and** a projected tracker comment; a **tracker-only** item (no spec) parks in the tracker comment alone. Projection is transport-blind across GitHub / GitLab / Jira / Linear via tracker-sync's adapter; no transport \u21d2 spec-only (when a spec exists) + a one-line \"enable X to mirror\" note, never a block. Selection **skips any item carrying a `status=open` parked question**, so it is never re-picked. A human answer (flipping the spec anchor to `status=answered`, or a tracker reply carrying `<!-- flow-next:answer id=<hash> -->` matched by `id`) makes the next tick re-triage and proceed. Terminal verdict: `ASKED <id> (<n>)` \u2014 a durable park.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Decision log (`pilot-log`)",
          "definition": "The per-tick **factory-metrics substrate** backlog mode writes (fn-68) via `flowctl pilot-log append --id <id> --action <triaged|advanced|asked|blocked|needs-human> --stage <stage|-> [--cost-tokens <n>]`, summarized by `flowctl pilot-log summary --json` \u2192 `{tick, id, action, stage, costTokens}` rows. The action enum is **aligned to the verdict grammar**; token cost is **host-reported** (omitted/null when unavailable) \u2014 flowctl only stores the row, never measures cost. Rows yield the efficiency readout (% moved with no question / one async answer / parked, and cost per change) and are the substrate a future self-improvement-synthesis spec mines. Stored under `.flow/pilot-runs/` (a sync-runs-style dir, auto-gitignored) \u2014 deliberately **NOT** any `receipts/` path the ralph-guard validates.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Land",
          "definition": "The cadence-tick ship loop (`/flow-next:land`): one tick discovers the open PRs the build loop authored (spec `branch_name` match AND the make-pr breadcrumb \u2014 both signals required), walks each through the gate tree (CI tri-state over ALL checks, patience window anchored to the last push, resolve-pr convergence, `land.reviewSignal`), and takes at most one action class per PR \u2014 CI fix, resolve dispatch, mechanical rebase, or the gated explicit merge (`gh pr merge --squash --match-head-commit`, never `--auto`) plus the post-merge tail (spec close \u2192 tracker touchpoint \u2192 release-follow). The one confined exception to the no-auto-merge rule; `/loop`-shaped where pilot is `/goal`-shaped. Ends with a terminal `LAND_VERDICT` line.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "QA stage (`pipeline.qa`)",
          "definition": "The optional live-app QA pass `/flow-next:qa`, graduated into a config-gated pilot stage (`pipeline.qa`, default **off**). When on, pilot runs one live pass over the complete build at all-tasks-done \u2014 `plan -> plan-review -> work -> **qa** -> make-pr` \u2014 driving the app the dev already has running during `work`. **Evidence-aware** (subtracts only AC a deterministic re-runnable check already proved; always live-runs every runtime / UI / integration criterion because the worker's self-report is narration, not captured evidence), **surfaced not blocking** (routes on `qa_outcome`, NOT the Ralph-guard `verdict` projection \u2014 `SHIP`/`NA`/`BLOCKED` advance, `NEEDS_WORK` still advances to the **draft** PR with findings in a `## Live QA` section + the bug-memory track + a tracker comment), and **augments, never replaces** CI / staging / manual QA. Net-new is one config-key default plus additive `qa_verdict` receipt fields (`head_sha` / `rid_coverage` / `open_p0p1`) \u2014 no new flowctl subcommand, no persisted test-case artefact. Idempotent per branch head via the receipt's `head_sha`. See `skills/flow-next-qa/SKILL.md` (fn-72).",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Verdict",
          "definition": "The structured tick outcome a loop skill prints for transcript-blind drivers, always the last line of a tick. Pilot: `PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason=\"<one line>\"`; [backlog mode](#backlog-mode-pilotautonomy) **adds `ASKED <id> (<n>)`** (a durable park) and keeps every existing terminal verbatim (drivers grep `DEFERRED_TO_LAND` for the land hand-off, stop on `NO_WORK`); `TRIAGED <id> <class>` is diagnostic / `--dry-run` only, never a live terminal. Land: `LAND_VERDICT=<MERGED|RELEASED|FIXING_CI|AWAITING_REVIEW|RESOLVING|BLOCKED|NEEDS_HUMAN|NO_WORK> prs=<n> pr=<deciding-pr-url|-> reason=\"<one line>\"` (tick verdict = worst severity across PRs). Autonomous resolve-pr runs end with `RESOLVE_PR_VERDICT=<RESOLVED|PENDING|NEEDS_HUMAN> threads=<n> fixed=<n> needs_human=<n>`, which land gates on. Distinct from a review receipt (Ralph's file-based proof-of-work): a verdict lives in the conversation output because `/goal` validators read the transcript, never the filesystem.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Spec-as-PR",
          "definition": "A team workflow where the spec is opened as a draft PR for review BEFORE any code lands. Reviewing a 50-line spec is higher-leverage than reviewing a 500-line implementation. Once merged, the spec is frozen on main; implementation PRs reference the merged spec.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Frozen-at-handover",
          "definition": "The R-ID invariant. Once a spec has been reviewed once, R5 means the same thing forever. A reviewer reading R5 in a six-month-old commit, a new team member reading R5 in the spec, and `/flow-next:make-pr` emitting R5 coverage all refer to the same acceptance criterion. Renumber-forbidden after first review cycle.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "flow-swarm",
          "definition": "An in-progress companion product to flow-next that reads `.flow/specs/` directly to coordinate parallel agents across worktrees and consume `/flow-next:make-pr` output. The on-disk layout flow-swarm expects is what fn-43 (epic->spec rename) produces. Reference target for the v1.0 migration carrot.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Tracker",
          "definition": "An external issue tracker (Linear, GitHub Issues, GitLab, or Jira) that flow-next *projects* a spec to via `/flow-next:tracker-sync`. The tracker is a **co-editable mirror** \u2014 body, status, and comments sync two-way \u2014 but it is **projection, not coordination**: the `.flow/specs/<id>.md` spec stays the source of truth and the quality layer, and the tracker never drives flow state or spawns agents. Distinct from `/flow-next:sync` (plan-sync). Contrast OpenAI Symphony, where the tracker *is* the control plane.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "merge-base snapshot",
          "definition": "The common-ancestor body the tracker-sync 3-way merge compares against \u2014 a **paired** snapshot taken at the last sync point: both a flow-form body and a tracker-form body, plus content hashes (the echo fence). Stored in the spec-JSON `tracker` block (`mergeBaseFlow` / `mergeBaseTracker` / `baseHashFlow` / `baseHashTracker`) and written atomically as a unit (a one-sided update is rejected, so neither half pins to a stale sync point). Advances with `lastSyncedAt` on a real reconcile, never on a no-op echo.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "discovery ceremony",
          "definition": "The detect \u2192 surface \u2192 ask \u2192 never-assume flow `/flow-next:tracker-sync` runs before enabling the bridge. It probes six signals (Linear MCP, `LINEAR_API_KEY`, GitHub auth, GitLab auth/`GITLAB_TOKEN`, Jira REST + token \u2014 `JIRA_BASE_URL` plus Cloud `JIRA_EMAIL`+`JIRA_API_TOKEN` or DC/Server `JIRA_PAT`), surfaces what is present *and* absent, asks the user, and writes `tracker.*` config **only on confirmation**, with provenance. No signal \u21d2 nothing written; the bridge stays off. Resolution model is env > config > ask (mirrors `flowctl review-backend`).",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "tracker-key handle",
          "definition": "A tracker identifier (e.g. `WOR-17`) used as a **resolvable flow id**, the hybrid id model. **Tracker-first** specs are canonically `wor-17-slug` (tasks `wor-17-slug.M`); bare `wor-17` / `wor-17.M` resolve as aliases. **Flow-first** specs keep `fn-NN-slug` and store `WOR-17` in `tracker.identifier` as a resolvable display alias. Resolution is case-insensitive (`show wor-17`, `work wor-17` resolve); the native `fn-` scheme is reserved (`fn-N` allocation counts `fn-*` only); one tracker team per repo; **ids never rename** on link.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "dependency projection",
          "definition": "Tracker-sync's projection of a spec's local `depends_on_epics` edges into **tracker issue relations** (fn-64) \u2014 a `depends_on_epics` edge between two linked specs becomes a **blocked-by** relation between their issues (Linear native relations / GitHub native dependencies / GitLab native `is_blocked_by` issue links / Jira native \"is blocked by\" issue links \u2014 directional and universally available, no licence gate, no `flow:deps` block \u2014 else, for GitHub's reduced rung and GitLab on every tier, a provenance-fenced `<!-- flow:deps -->` body block). The relations counterpart to body/status/comments sync: projection, not coordination \u2014 flow stays authoritative, the tracker never declares deps back. Runs through the transport-blind `projectDepRelations` hook + the normalized `setIssueRelation` / `listIssueRelations` adapter pair; idempotent via read-before-write. No transitive/graph expansion \u2014 only direct edges project.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "provenance ledger",
          "definition": "The per-spec `depRelations` list (in the `.flow/specs/<id>.json` `tracker` block, atomic write) that records **which** dependency relations tracker-sync created \u2014 so projection is idempotent and removals are provably-ours-only. Each entry is `{key, dep_spec, from_tracker_id, to_tracker_id, type, source, updatedAt}`, where `key` is an opaque hash of the directed issue pair (never a raw issue key inline \u2014 trackers auto-linkify keys even inside HTML comments). A relation **not** in the ledger (native trackers) / **outside** the `<!-- flow:deps -->` fenced block (GitHub's fenced fallback; GitLab's block on every tier) is never removed: a human's manual relation is safe by construction. Mirrors the merge-base hash-provenance shape, minus its paired-snapshot constraint.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "completed-blocker rule",
          "definition": "The tracker-sync semantics for a dependency whose **local** dep spec is `done` (\u2192 its issue Done/Closed): the projected blocked-by relation stays **visible** on the tracker (preserving the real historical ordering on the board) but does **NOT** feed back into Flow `ready=true` gating \u2014 readiness already treats done deps as satisfied, and dependency projection must not regress that. Keys off the *local* dep-spec status (flow is authoritative), never a remote fetch.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "render lens",
          "definition": "A regenerable human-review artifact (HTML) derived from a markdown source of truth; never the storage format, always re-derivable. flow-next ships two: the spec artifact and the PR artifact, both living at fixed deterministic paths under `.flow/artifacts/<spec-id>/` (never timestamped \u2014 Lavish keys annotation sessions on the absolute path). Every lens is self-contained single-file HTML (inline CSS/JS, zero external requests), carries a staleness stamp in its footer, and is never parsed back as state \u2014 regeneration always overwrites the same file.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "HTML artifact mode",
          "definition": "The opt-in feature (2.0.0+) that makes participating skills (capture, plan, make-pr) emit render lenses alongside their markdown output. Activated via `flowctl config set artifacts.html.enabled true` (OFF by default, offered once by `/flow-next:setup`); when active, skills load the shared disclosure reference at `plugins/flow-next/references/html-artifacts.md` \u2014 the single carrier of all generation rules and the anti-slop design contract. With the mode off, skills load nothing extra: zero token cost, zero behavior change. Markdown and tracker-sync remain the sole source of truth.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "spec artifact",
          "definition": "The spec's render lens at `.flow/artifacts/<spec-id>/spec.html`. ONE generation pathway with state-dependent rendering: spec-only view before tasks exist (capture workflow \u00a75.10 \u2014 the business-review surface) and the added plan layer (task dependency DAG with critical path, R-ID \u2192 task coverage matrix) once tasks exist (plan Step 8.5 \u2014 after the refinement loop exits). Links back from the spec markdown via the idempotent `<!-- flow-next:artifact-link -->` marker line (replaced in place, repo-relative target). The only artifact that enters the Lavish annotate loop.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "PR artifact",
          "definition": "The PR's render lens at `.flow/artifacts/<spec-id>/pr.html`, emitted by `/flow-next:make-pr` Phase 1.5. A **read-only review instrument**: diff-derived (never from commit messages), verified against the spec's R-ID export before publishing \u2014 mismatches render as visibly flagged rows, warn-in-artifact, never blocking. Committed narrowly (`chore(flow): pr artifact <spec-id>`, artifact file only) so the PR body's SHA-pinned blob link resolves; never enters the annotate loop \u2014 review conversation belongs to the code host.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Lavish (lavish-axi)",
          "definition": "An optional detect-on-PATH companion (npm: `lavish-axi`) for annotating spec artifacts in the browser \u2014 never wrapped, bundled, or required (same shape as clawpatch/`/flow-next:map`). Feedback is pull-only and session-spanning: annotations queue in the global `~/.lavish-axi/state.json` (not per-workspace), survive agent death, and any later agent session drains them via the `lavish-axi poll` CLI, mapping each annotation to a markdown-source edit followed by lens regeneration. Sessions key on the absolute artifact path (different worktrees = separate sessions); the local server idle-stops after ~30 min and `lavish-axi <file>` resumes it \u2014 absence or idle-stop is invisible because the artifact is a self-contained static page. Autonomous contexts never open a session and never poll.",
          "avoid": [],
          "relates_to": []
        }
      ],
      "count": 38
    }
  ],
  "file_count": 1,
  "total_terms": 38
}
