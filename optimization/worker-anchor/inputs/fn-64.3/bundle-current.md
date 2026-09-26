# Worker anchor bundle - fn-64-tracker-sync-project-flow-spec.3 (spec fn-64-tracker-sync-project-flow-spec)

Verbatim outputs of the worker Phase-1 re-anchor reads, fixed order, no filtering or truncation. The bundle is a floor, not a ceiling - memory keyword-search and every further read remain available.

===== [1/11] task_show: `flowctl show fn-64-tracker-sync-project-flow-spec.3 --json` =====
{
  "success": true,
  "assignee": null,
  "claim_note": "",
  "claimed_at": null,
  "created_at": "2026-06-16T15:27:50.438599Z",
  "depends_on": [
    "fn-64-tracker-sync-project-flow-spec.2"
  ],
  "id": "fn-64-tracker-sync-project-flow-spec.3",
  "priority": null,
  "spec": "fn-64-tracker-sync-project-flow-spec",
  "spec_path": ".flow/tasks/fn-64-tracker-sync-project-flow-spec.3.md",
  "status": "todo",
  "title": "Linear adapter relation transport (MCP save_issue + GraphQL issueRelationCreate, read-before-write dedup)",
  "updated_at": "2026-06-16T15:40:26.761207Z",
  "impl": null,
  "review": null,
  "sync": null,
  "status_source": "committed"
}

===== [2/11] task_md: `flowctl cat fn-64-tracker-sync-project-flow-spec.3` =====
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

===== [3/11] spec_show: `flowctl show fn-64-tracker-sync-project-flow-spec --json` =====
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
  "plan_review_rounds": 0,
  "impl_review_rounds": {},
  "tasks": [
    {
      "id": "fn-64-tracker-sync-project-flow-spec.1",
      "title": "flowctl: depRelations sync state + list/set/clear-dep-relation subcommands + unit tests",
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": []
    },
    {
      "id": "fn-64-tracker-sync-project-flow-spec.2",
      "title": "Adapter interface contract: setIssueRelation / listIssueRelations + relation struct",
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": []
    },
    {
      "id": "fn-64-tracker-sync-project-flow-spec.3",
      "title": "Linear adapter relation transport (MCP save_issue + GraphQL issueRelationCreate, read-before-write dedup)",
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": [
        "fn-64-tracker-sync-project-flow-spec.2"
      ]
    },
    {
      "id": "fn-64-tracker-sync-project-flow-spec.4",
      "title": "GitHub adapter relation transport (native REST deps + fenced body-block fallback, #N parsing)",
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": [
        "fn-64-tracker-sync-project-flow-spec.2"
      ]
    },
    {
      "id": "fn-64-tracker-sync-project-flow-spec.5",
      "title": "projectDepRelations transport-blind skill hook (steps.md/SKILL.md): push+reconcile, warnings, completed-blocker, never-clobber, receipts",
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
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
      "status": "todo",
      "status_source": "committed",
      "implicit_owner": false,
      "priority": null,
      "depends_on": [
        "fn-64-tracker-sync-project-flow-spec.1",
        "fn-64-tracker-sync-project-flow-spec.5"
      ]
    }
  ],
  "no_plan": false
}

===== [4/11] spec_md: `flowctl cat fn-64-tracker-sync-project-flow-spec` =====
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

===== [5/11] git_status: `git status` =====
On branch fn-258-smaller-default-outputs-and-bundles
Your branch is ahead of 'origin/main' by 1 commit.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   agent_docs/adding-skills.md
	modified:   optimization/worker-anchor/run_eval.py
	modified:   plugins/flow-next/agents/repo-scout.md
	modified:   plugins/flow-next/agents/spec-scout.md
	modified:   plugins/flow-next/agents/worker.md
	modified:   plugins/flow-next/codex/agents/repo-scout.toml
	modified:   plugins/flow-next/codex/agents/spec-scout.toml
	modified:   plugins/flow-next/codex/agents/worker.toml
	modified:   plugins/flow-next/codex/docs/flow-next/flowctl.md
	modified:   plugins/flow-next/codex/docs/flow-next/glossary.md
	modified:   plugins/flow-next/codex/skills/flow-next-capture/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-features/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-impl-review/workflow-codex.md
	modified:   plugins/flow-next/codex/skills/flow-next-impl-review/workflow-host.md
	modified:   plugins/flow-next/codex/skills/flow-next-impl-review/workflow-rp.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-claude.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-codex.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-copilot.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-cursor.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-host.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow-rp.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan-review/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-plan/references/selected-review.md
	modified:   plugins/flow-next/codex/skills/flow-next-refine/references/pass-business.md
	modified:   plugins/flow-next/codex/skills/flow-next-resolve-pr/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-resolve-pr/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-setup/templates/agents-md-snippet.md
	modified:   plugins/flow-next/codex/skills/flow-next-setup/templates/claude-md-snippet.md
	modified:   plugins/flow-next/codex/skills/flow-next-setup/workflow.md
	modified:   plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-host.md
	modified:   plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-rp.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/adapter-interface.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/body-merge.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/comments-sync.md
	modified:   plugins/flow-next/codex/skills/flow-next-tracker-sync/references/status-sync.md
	modified:   plugins/flow-next/codex/skills/flow-next-work/SKILL.md
	modified:   plugins/flow-next/codex/skills/flow-next-work/phases.md
	modified:   plugins/flow-next/codex/skills/flow-next-work/references/host-deferred-review.md
	modified:   plugins/flow-next/codex/skills/flow-next/SKILL.md
	modified:   plugins/flow-next/commands/audit.md
	modified:   plugins/flow-next/commands/capture.md
	modified:   plugins/flow-next/commands/chart.md
	modified:   plugins/flow-next/commands/features.md
	modified:   plugins/flow-next/commands/flow.md
	modified:   plugins/flow-next/commands/impl-review.md
	modified:   plugins/flow-next/commands/land.md
	modified:   plugins/flow-next/commands/make-pr.md
	modified:   plugins/flow-next/commands/map.md
	modified:   plugins/flow-next/commands/memory-migrate.md
	modified:   plugins/flow-next/commands/plan-review.md
	modified:   plugins/flow-next/commands/plan.md
	modified:   plugins/flow-next/commands/prime.md
	modified:   plugins/flow-next/commands/prose.md
	modified:   plugins/flow-next/commands/prospect.md
	modified:   plugins/flow-next/commands/qa.md
	modified:   plugins/flow-next/commands/ralph-init.md
	modified:   plugins/flow-next/commands/refine.md
	modified:   plugins/flow-next/commands/resolve-pr.md
	modified:   plugins/flow-next/commands/setup.md
	modified:   plugins/flow-next/commands/spec-completion-review.md
	modified:   plugins/flow-next/commands/strategy.md
	modified:   plugins/flow-next/commands/sync.md
	modified:   plugins/flow-next/commands/tracker-sync.md
	modified:   plugins/flow-next/commands/uninstall.md
	modified:   plugins/flow-next/commands/visual.md
	modified:   plugins/flow-next/commands/work.md
	modified:   plugins/flow-next/docs/flowctl.md
	modified:   plugins/flow-next/docs/glossary.md
	modified:   plugins/flow-next/scripts/flowctl.py
	modified:   plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json
	modified:   plugins/flow-next/skills/flow-next-capture/workflow.md
	modified:   plugins/flow-next/skills/flow-next-features/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-flow/auto.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/backlog-mode.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/gate-selection.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/plan-vs-no-plan.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/route-matrix.md
	modified:   plugins/flow-next/skills/flow-next-flow/references/tail.md
	modified:   plugins/flow-next/skills/flow-next-flow/workflow.md
	modified:   plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md
	modified:   plugins/flow-next/skills/flow-next-impl-review/workflow-host.md
	modified:   plugins/flow-next/skills/flow-next-impl-review/workflow-rp.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-claude.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-codex.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-copilot.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-cursor.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-host.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md
	modified:   plugins/flow-next/skills/flow-next-plan-review/workflow.md
	modified:   plugins/flow-next/skills/flow-next-plan/references/selected-review.md
	modified:   plugins/flow-next/skills/flow-next-refine/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-refine/references/pass-business.md
	modified:   plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-resolve-pr/workflow.md
	modified:   plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md
	modified:   plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md
	modified:   plugins/flow-next/skills/flow-next-setup/workflow.md
	modified:   plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md
	modified:   plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md
	modified:   plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md
	modified:   plugins/flow-next/skills/flow-next-work/SKILL.md
	modified:   plugins/flow-next/skills/flow-next-work/phases.md
	modified:   plugins/flow-next/skills/flow-next-work/references/host-deferred-review.md
	modified:   plugins/flow-next/skills/flow-next-work/references/rolling-scheduler.md
	modified:   plugins/flow-next/skills/flow-next-work/references/wave-join.md
	modified:   plugins/flow-next/skills/flow-next/SKILL.md
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-capture-brief.json
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-chart.json
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-interview.json
	modified:   plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-skip-chart-clear.json
	modified:   plugins/flow-next/tests/test_anchor_bundle.py
	modified:   plugins/flow-next/tests/test_flow_merge_destination.py
	modified:   plugins/flow-next/tests/test_parallel_work_prose.py
	modified:   plugins/flow-next/tests/test_pilot_chain_stages.py
	modified:   plugins/flow-next/tests/test_precheck_mode_contract.py
	modified:   plugins/flow-next/tests/test_review_convergence_cap.py
	modified:   plugins/flow-next/tests/test_setup_snippet_lockstep.py
	modified:   scripts/sync-codex.sh

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	optimization/worker-anchor/gen_fn258_inputs.py
	plugins/flow-next/codex/skills/flow-next-tracker-sync/references/chart-subjects.md
	plugins/flow-next/skills/flow-next-tracker-sync/references/chart-subjects.md
	plugins/flow-next/tests/test_glossary_match.py
	plugins/flow-next/tests/test_skill_id_invocations.py

no changes added to commit (use "git add" and/or "git commit -a")

===== [6/11] git_log: `git log -5 --oneline` =====
c13a4d52 chore(flow): record fn-258 direct route and mint the owner task
e5535836 Correctness and hygiene sweep (audit wave 3) (#472)
b4c980af Unattended-run correctness fixes (audit wave 1) (#470)
9509a2cf Test suite and CI wall-clock (audit wave 2) (#471)
b334b5d7 chore(flow-next): bump version to 6.0.2

===== [7/11] git_branch: `git rev-parse --abbrev-ref HEAD` =====
fn-258-smaller-default-outputs-and-bundles

===== [8/11] memory_enabled: `flowctl config get memory.enabled --json` =====
{
  "success": true,
  "key": "memory.enabled",
  "value": true
}

===== [9/11] glossary: `flowctl glossary list --json` =====
{
  "success": true,
  "groups": [
    {
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/GLOSSARY.md",
      "entries": [
        {
          "term": "Spec",
          "definition": "The unit of intent: `.flow/specs/<id>.md` (body) + `.flow/specs/<id>.json` (metadata sidecar). Reviewable on its own, cross-model reviewed, frozen at handover. One spec is a stream of work, not a sprint item \u2014 it holds acceptance criteria (R-IDs), not a to-do list.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Task, R-ID, Chart",
          "avoid": [
            "epic",
            "ticket",
            "story",
            "PRD",
            "requirements doc"
          ],
          "relates_to": [
            "Task",
            "R-ID",
            "Chart"
          ]
        },
        {
          "term": "Task",
          "definition": "An execution unit under a spec (`fn-N.M`), sized to one `/flow-next:work` iteration (~100k tokens of fresh context). Declares `requires:` dependencies and optionally the R-IDs it `satisfies:`. Implemented by a worker subagent, never by the conductor directly.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Wave",
          "avoid": [
            "subtask",
            "ticket",
            "issue",
            "story"
          ],
          "relates_to": [
            "Spec",
            "Wave"
          ]
        },
        {
          "term": "R-ID",
          "definition": "A numbered acceptance criterion in a spec, written `**R1:** ...`. Renumber-forbidden after the first review cycle: deletions leave gaps, new criteria take the next unused number. The load-bearing identity of a requirement across the spec, the tasks that satisfy it, the commits, and the PR coverage table. `G1`, `G2` in `.flow/criteria.md` are the same grammar lifted to project scope. An R-ID is judged against evidence at review; it is never required to pre-exist as an executable test (the ATDD contract, which flow-next deliberately does not adopt).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Task",
          "avoid": [
            "AC-1",
            "requirement #1",
            "renumbering",
            "req id"
          ],
          "relates_to": [
            "Spec",
            "Task"
          ]
        },
        {
          "term": "Wave",
          "definition": "A set of tasks whose dependencies are all satisfied at the same point \u2014 the parallel candidates `/flow-next:plan` reports. A wave is a scheduling fact derived from the dependency graph, not a time box and not a mandate to share one checkout: parallel workers get isolated workspaces and the conductor joins the wave before review.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Task",
          "avoid": [
            "sprint",
            "phase",
            "batch",
            "iteration"
          ],
          "relates_to": [
            "Task"
          ]
        },
        {
          "term": "Chart",
          "definition": "Optional pre-capture decision mapping (`/flow-next:chart`) for one idea too large or unclear to capture in a single session: decisions (`D1`, `D2`, ...) under `.flow/charts/`, exiting as a briefing package for `/flow-next:capture`. Chart makes an effort understandable enough to plan; plan decomposes work already understood; prospect ranks plural candidate ideas. Never writes a spec, never sets `ready`.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Task",
          "avoid": [
            "discovery doc",
            "RFC",
            "design doc",
            "plan",
            "prospect"
          ],
          "relates_to": [
            "Spec",
            "Task"
          ]
        },
        {
          "term": "Receipt",
          "definition": "A JSON artefact on disk that proves a step happened and gates the next one \u2014 review receipts under `.flow/review-receipts/`, green receipts under `.flow/tmp/green-receipts/`, QA verdict receipts. A receipt is a file; a verdict is the terminal line a loop skill prints into the transcript for its driver (`PILOT_VERDICT=`, `LAND_VERDICT=`). Never use one word for the other.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Gate, Review backend",
          "avoid": [
            "report",
            "log",
            "verdict",
            "summary"
          ],
          "relates_to": [
            "Gate",
            "Review backend"
          ]
        },
        {
          "term": "Gate",
          "definition": "A pass/fail check the workflow refuses to proceed past \u2014 the repo's full local quality gate (lint, typecheck, tests, docs) run before handoff, plus the review and readiness gates in the pipeline. A green receipt is the proof one exact gate command passed at one exact commit; `flowctl gate check` decides whether that proof still applies. Gates are local and fail-closed; CI is a separate surface.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Receipt",
          "avoid": [
            "check",
            "hook",
            "CI",
            "guardrail"
          ],
          "relates_to": [
            "Receipt"
          ]
        },
        {
          "term": "Anchor",
          "definition": "Re-reading the spec, the task, and git state before work continues, so long sessions do not drift. `flowctl anchor <task-id>` is the per-task bundle a worker reads every iteration; `flowctl brief` is the cold-session equivalent. Not `/flow-next:prime`, which assesses whether a repo is ready for agents at all.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Task, Spec",
          "avoid": [
            "context refresh",
            "priming",
            "warm-up",
            "reload"
          ],
          "relates_to": [
            "Task",
            "Spec"
          ]
        },
        {
          "term": "plan-sync",
          "definition": "`/flow-next:sync` \u2014 the internal pass that updates *downstream task specs* after implementation drift, inside `.flow/`. Do not confuse it with tracker-sync (`/flow-next:tracker-sync`), which projects a spec *outward* to Linear / GitHub / GitLab / Jira and reconciles body, status, and comments. Bare \"sync\" is ambiguous and should not be used for either.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Spec, Task",
          "avoid": [
            "sync",
            "tracker-sync",
            "resync"
          ],
          "relates_to": [
            "Spec",
            "Task"
          ]
        },
        {
          "term": "Review backend",
          "definition": "The engine that performs a cross-model review: `rp` (RepoPrompt), `codex`, `copilot`, `cursor`, `claude`, `host`, or `none`, resolved by the `review.backend` grammar (env > per-spec/task > config). The backend is the review *mechanism*, distinct from the model it happens to run and from the reviewing agent's findings.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Receipt",
          "avoid": [
            "judge",
            "provider",
            "model"
          ],
          "relates_to": [
            "Receipt"
          ]
        },
        {
          "term": "Memory",
          "definition": "Categorized durable learnings under `.flow/memory/` \u2014 `bug/<category>/` and `knowledge/<category>/` entries with YAML frontmatter, searched via `flowctl memory search`. Memory is audited, superseded, and graduated into gates; it is not a scratchpad and not a substitute for docs or code comments.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Gate",
          "avoid": [
            "notes",
            "scratchpad",
            "context files",
            "learnings dump"
          ],
          "relates_to": [
            "Gate"
          ]
        },
        {
          "term": "Spine",
          "definition": "The always-loaded body of a `SKILL.md` under branch disclosure: the universal path every run needs, with branch-only content read from `references/*.md` at the branch point. A reference is the cold-path file; the spine is the hot path. Safety nets and every-run contracts stay in the spine by rule.",
          "avoid": [
            "prompt",
            "main file",
            "header",
            "preamble"
          ],
          "relates_to": []
        },
        {
          "term": "Tier",
          "definition": "What kind of model a job wants: `reviewer`, `implementer`, `fast scout`, `thinking scout`, or unset (the session model). A tier binds a model to a stage's execution, never to which stages run \u2014 which stages run is decided by what you invoked. The four names are a user-facing interface defined in exactly one place, [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants); an unrecognized name is treated as unset with one advisory.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Reach, Review backend",
          "avoid": [
            "pin",
            "model tier",
            "capability level",
            "role map"
          ],
          "relates_to": [
            "Reach",
            "Review backend"
          ]
        },
        {
          "term": "Reach",
          "definition": "How the active harness obtains a model for a tier: the in-session model, an in-host subagent, shelling out to another CLI, or not available. Documented once per harness under [`plugins/flow-next/docs/reach/`](plugins/flow-next/docs/reach/README.md) and never inside a skill \u2014 a skill asks for a tier and names no spawn primitive, CLI flag, or vendor path. An undetectable harness resolves to the generic page and says so.\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier",
          "avoid": [
            "dispatch mechanism",
            "availability",
            "probe"
          ],
          "relates_to": [
            "Tier"
          ]
        },
        {
          "term": "Reviewer tier",
          "definition": "The tier for anything grading work someone else produced. The only tier carrying a family rule: a reviewer from the writer's own family is not an independent verdict. The rule is advice, not enforcement \u2014 the receipt records what ran, and nothing fails closed on it. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier, Review backend",
          "avoid": [
            "grader",
            "review model",
            "critic"
          ],
          "relates_to": [
            "Tier",
            "Review backend"
          ]
        },
        {
          "term": "Implementer tier",
          "definition": "The tier for work handed to another harness \u2014 plan on the session model, implement somewhere cheaper or faster. Absent, the session model implements. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier, Task",
          "avoid": [
            "bridged worker",
            "executor"
          ],
          "relates_to": [
            "Tier",
            "Task"
          ]
        },
        {
          "term": "Fast scout tier",
          "definition": "The tier for mechanical inventory scanning, where the cheapest model is the correct one. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier",
          "avoid": [
            "cheap tier",
            "scanner model",
            "fast model",
            "low tier"
          ],
          "relates_to": [
            "Tier"
          ]
        },
        {
          "term": "Thinking scout tier",
          "definition": "The tier for analysis that degrades badly on a fast model \u2014 requirement analysis and pattern judgment, not scans. Canonical definition: [`plugins/flow-next/docs/orchestration.md`](plugins/flow-next/docs/orchestration.md#tiers-what-kind-of-model-a-job-wants).\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_Relates to_: Tier",
          "avoid": [
            "judgment tier",
            "smart scout",
            "intelligent scout",
            "deep scout"
          ],
          "relates_to": [
            "Tier"
          ]
        },
        {
          "term": "Emission point",
          "definition": "A named step in a skill or agent where durable user-facing prose is drafted (make-pr body rendering, tracker-sync comment composition, capture/refine/plan spec prose, chart briefings, strategy sections, qa finding bodies, land verdict output, prospect candidates, prime glossary definitions, audit memory entries, worker done summaries, resolve-pr replies, changelog entries). Emission points cite the prose contract by path, passing the identity and never a copied payload.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "No-plan route",
          "definition": "Execution through `/flow-next:work <spec-id> --no-plan`, the default route for a ready cohesive spec and a capable coding agent. Plan is chosen only on a positive signal; the signals and the exclusions are in [`plan-vs-no-plan.md`](plugins/flow-next/skills/flow-next-flow/references/plan-vs-no-plan.md). Work records the accepted choice and creates one implicit owner task covering every spec R-ID. Resume and `flow --auto` continuation retain that route. Separate task planning and its automatic plan review are omitted; explicit spec/design review, configured implementation review, coverage, completion-review policy and opt-in QA retain their contracts.",
          "avoid": [
            "plan-less mode",
            "skip-plan flag",
            "zero-task execution"
          ],
          "relates_to": [
            "Spec",
            "Task",
            "R-ID"
          ]
        },
        {
          "term": "Feature map",
          "definition": "The committed user-POV directory (`.flow/features/`) recording how a user reaches and drives each user-facing feature, consumed by QA/drive for navigation; distinct from the code-POV `/flow-next:map` index.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Doctor",
          "definition": "The one read-only health check a drive-capable run performs before driving an instance (right build, owned port, valid auth), answering \"is this instance worth driving\".",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Routing reference",
          "definition": "The set of six small reference files the flow skill owns under `plugins/flow-next/skills/flow-next-flow/references/`, one per routing rule, progressively disclosed through step-scoped conditional pointers so the agent reads only the files the current step needs: `route-matrix.md`, `spec-count.md`, `plan-vs-no-plan.md`, `gate-selection.md`, `prototype-before-ask.md`, and `tail.md`. Each opens with a decision record. Flow, `flow --explain`, `flow --auto`, capture's closer, plan's next-steps menu, and work's zero-task ask read the same files. The same directory also holds two gated auto-only references (`backlog-mode.md`, `qa-stage.md`) that `auto.md` reads under `--backlog` and the QA gate; they are workflow, not routing rules, and carry no decision record.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Driver",
          "definition": "The thing that invokes the unattended conductor and owns repetition: a human running `/flow-next:flow --auto` once per item, a host loop primitive (`/loop`, `/goal`, `cron`) running `flow --auto --tick`, or Ralph (the deprecated repo-local hardened harness). Attended `/flow-next:flow` stops at the next human decision; `flow --auto` stops at the next decision that needs a human and reports it as a verdict. Drivers are never recursively nested. The confined composition exception is flow invoking one land tick as its authorized landing stage for the selected spec and PR. Attended flow refuses under any autonomy marker, `flow --auto` refuses under Ralph, and land never dispatches a second driver.",
          "avoid": [
            "mode",
            "conductor mode",
            "autopilot"
          ],
          "relates_to": [
            "Routing reference",
            "Hop",
            "Tick",
            "Long-horizon run",
            "Pilot"
          ]
        },
        {
          "term": "Hop",
          "definition": "One route-run-re-evaluate cycle of `/flow-next:flow`: classify the item from the routing reference, run the routed stage, verify from observed state, record the outcome. Under `--auto` every hop ends with committed receipts, one evidence echo, one `stage: <name> - ran | skipped(<reason>) | failed(<reason>)` line, and a ledger write, so a run that dies mid-way resumes from disk on the next invocation; nothing is resumed from transcript. The hop is the handover unit between the driver and the pipeline.",
          "avoid": [
            "step",
            "iteration",
            "turn"
          ],
          "relates_to": [
            "Driver",
            "Tick",
            "Long-horizon run"
          ]
        },
        {
          "term": "Tick",
          "definition": "Exactly one hop of `flow --auto`, selected with `--tick`. The run classifies, dispatches one stage, verifies, records, and stops with the verdict line. A landing hop consumes at most one land tick. The portable floor for hosts without stable long sessions, run under the host's loop primitive (`/loop 30m /flow-next:flow --auto --tick`). What a `/flow-next:pilot` invocation was.",
          "avoid": [
            "pilot tick",
            "single-stage run"
          ],
          "relates_to": [
            "Hop",
            "Long-horizon run",
            "Driver",
            "Pilot"
          ]
        },
        {
          "term": "Long-horizon run",
          "definition": "The default shape of `flow --auto`: one invocation drives one ready item hop after hop until a terminal (a PR exists, deferred to land, asked, blocked, needs human, no work). With `--until=merge`, it can continue through land ticks and external waits until the selected PR is confirmed merged, or an existing stop condition applies. The verdict line names every dispatched stage in order joined by `+` (`stage=work+qa+make-pr`) and carries the last hop's verdict. One item per run; the next invocation selects the next item.",
          "avoid": [
            "multi-stage tick",
            "chained tick",
            "autopilot run"
          ],
          "relates_to": [
            "Hop",
            "Tick",
            "Verdict line"
          ]
        },
        {
          "term": "Verdict line",
          "definition": "The terminal line every `flow --auto` run and every `/flow-next:land` tick prints last, for the driver to read: `PILOT_VERDICT=<ADVANCED|ASKED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason=\"<one line>\"` and `LAND_VERDICT=...`. The `PILOT_VERDICT` name is kept unchanged across the pilot retirement so existing drivers keep parsing; `TRIAGED` appears under `--explain` and `--dry-run` only. Under a merge destination, the reason and observed evidence distinguish landing progress, external waiting, blockage, confirmed merge, and any tracker touchpoint failure; the original `LAND_VERDICT` is retained in the evidence.",
          "avoid": [
            "exit status",
            "summary line",
            "result banner"
          ],
          "relates_to": [
            "Driver",
            "Long-horizon run",
            "Tick"
          ]
        },
        {
          "term": "Pilot",
          "definition": "The deprecated alias for `/flow-next:flow --auto --tick`. Its `/flow-next:pilot` command is removed; the `flow-next-pilot` skill stub remains until the next release and maps `--spec <id>` to the positional id, passes `--backlog`, `--dry-run`, `--review`, `--research`, `--depth` through, prints one deprecation line to stderr, and behaves byte-for-byte as the tick. The spelling survives in config keys (`pilot.autonomy`, `pilot.gateClasses`), flowctl verbs (`flowctl pilot strikes`, `flowctl pilot-log`), the ledger and decision-log paths (`.flow/pilot-runs/`), and the `PILOT_VERDICT` name; those are not renamed.",
          "avoid": [
            "the pilot skill",
            "pilot loop",
            "build-loop conductor"
          ],
          "relates_to": [
            "Tick",
            "Driver",
            "Verdict line"
          ]
        },
        {
          "term": "Variant",
          "definition": "One worked route through the pipeline menu, named by its driving signal in `docs/pipeline-variations.md` and matched by a row of the route matrix: epic, feature with known requirements, no-plan, small task, bug or defect, refactoring, performance, hill climb, investigation, prototype, and docs or chore. Every variant keeps the same evidence, gate, and receipt contract; they differ only in which unknown they pay to convert.",
          "avoid": [
            "pipeline mode",
            "preset",
            "template pipeline"
          ],
          "relates_to": [
            "Routing reference",
            "No-plan route"
          ]
        },
        {
          "term": "Prototype-before-ask",
          "definition": "Classify a fork before asking the user. An answer observable by running something (behavior, output, timing, layout) is settled by a prototype or experiment. Only a product or preference call no experiment can settle becomes a question.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Refine",
          "definition": "The `/flow-next:refine` skill (`flow-next-refine`, renamed from `interview` in the flow release). A deep question pass over a spec, task, or spec file under a `business`, `technical`, or `both` scope, or the read-first research pass under `--scope=research`.",
          "avoid": [
            "interview skill",
            "interview command"
          ],
          "relates_to": []
        },
        {
          "term": "Research pass",
          "definition": "`/flow-next:refine --scope=research`: asks nothing; runs the read-only docs, practice, docs-gap, and memory scouts (github when gated on) and writes one `## Resolved via Research` section with a sub-block per scout and a source on every line. Skipped, with the reason printed, when the section or plan's scout findings already exist; `--force` reruns. Plan writes the same section when its research scouts run, so the pass never runs twice.",
          "avoid": [],
          "relates_to": [
            "Read-first signal",
            "Refine"
          ]
        },
        {
          "term": "Read-first signal",
          "definition": "The positive signal on the route matrix's ready-spec row: the spec names a library or API the repo does not already use. It sends the spec through the research pass before work on either route and is satisfied by a `## Resolved via Research` section or a plan that ran the scouts.",
          "avoid": [],
          "relates_to": []
        },
        {
          "term": "Why-scout",
          "definition": "The read-only agent for rationale questions. It anchors on `git blame` and the PRs behind the commits, reads the tracker thread through access the session already has, then the bug and decision memory tracks, and tiers each finding `direct`, `supported`, `inferred`, or `unknown`; the caller may not rewrite a tier. Named by the route matrix's investigation row for why questions.",
          "avoid": [],
          "relates_to": [
            "Thinking scout tier"
          ]
        },
        {
          "term": "Chain",
          "definition": "A dependent PR whose base is the parent spec's branch instead of the default branch (fn-152). Exists on any code host because it is only a branch and a base ref. A dependent spec is chain-eligible when its parent is open with every task done and its branch on origin, judged by `flowctl spec chain`, the one predicate every consumer calls; work then branches from the parent's remote tip and make-pr targets the parent's branch. Chains are linear: one open parent, one child at a time.",
          "avoid": [
            "stacked branch",
            "dependent branch",
            "branch-on-branch"
          ],
          "relates_to": [
            "Stack",
            "Layer",
            "Frontier",
            "Spec"
          ]
        },
        {
          "term": "Stack",
          "definition": "GitHub's server-side object over a chain: the linked PRs, the stack map in the merge box, sequential merge, and auto-retarget of the layers above a merged one. An enhancement of a chain, present only when the host is GitHub and make-pr's link call succeeded; on any other host, or after a failed link, the PR stands as a plain chain layer. Never a local file: the gh-stack extension is not required or read.",
          "avoid": [
            "gh-stack",
            "stacked diff",
            "Graphite stack"
          ],
          "relates_to": [
            "Chain",
            "Layer",
            "Frontier"
          ]
        },
        {
          "term": "Layer",
          "definition": "One PR in a chain or stack. The bottom layer is the open layer whose base is the chain's base branch (the default branch, or the branch a human chose); every other layer's base is the branch of the layer below it, so a reviewer sees only that layer's own diff.",
          "avoid": [
            "sub-PR",
            "child PR",
            "stacked PR"
          ],
          "relates_to": [
            "Chain",
            "Stack",
            "Frontier"
          ]
        },
        {
          "term": "Frontier",
          "definition": "The bottom open layer of a chain or stack, the only one that can merge next. Land merges at most one frontier per tick, from the bottom up; a human merging from GitHub's stack UI does the same. Distinct from the task frontier `flowctl ready` reports inside one spec.",
          "avoid": [
            "head of the stack",
            "top layer",
            "mergeable PR"
          ],
          "relates_to": [
            "Chain",
            "Stack",
            "Layer"
          ]
        }
      ],
      "count": 39
    }
  ],
  "file_count": 1,
  "total_terms": 39
}

===== [10/11] memory_index: `flowctl memory list --json` =====
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/backlog-select-must-not-drop-a-dep-2026-06-27.md"
    },
    {
      "entry_id": "bug/build-errors/canonical-3c-edits-vanish-from-codex-2026-08-28",
      "title": "Canonical 3c edits vanish from Codex mirror via stale SECTION3C heredoc",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh",
      "tags": [
        "fn-208",
        "sync-codex",
        "codex-mirror",
        "section3c",
        "dispatch-template",
        "codex-review"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/canonical-3c-edits-vanish-from-codex-2026-08-28.md"
    },
    {
      "entry_id": "bug/build-errors/changelog-entry-landed-in-a-released-2026-08-01",
      "title": "Changelog entry landed in a released section, not Unreleased",
      "track": "bug",
      "category": "build-errors",
      "module": "CHANGELOG.md",
      "tags": [
        "changelog",
        "release",
        "docs"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/changelog-entry-landed-in-a-released-2026-08-01.md"
    },
    {
      "entry_id": "bug/build-errors/codex-home-rewrite-both-spellings-2026-08-02",
      "title": "CODEX_HOME rewrite: both spellings, actionable prose, quoting, sorted-hash idemp",
      "track": "bug",
      "category": "build-errors",
      "module": "scripts/sync-codex.sh",
      "tags": [
        "codex",
        "installer",
        "generated-artifacts",
        "shell-quoting",
        "idempotency"
      ],
      "date": "2026-08-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/codex-home-rewrite-both-spellings-2026-08-02.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/codex-mirror-smoke-docs-miss-composed-2026-05-18.md"
    },
    {
      "entry_id": "bug/build-errors/concurrent-gating-draws-soft-terms-2026-08-21",
      "title": "Concurrent gating draws + soft terms falsify a 'frozen' eval pre-registration",
      "track": "bug",
      "category": "build-errors",
      "module": "agent-evals/studies/rolling-frontier-2026-08",
      "tags": [
        "fn-203",
        "eval-design",
        "pre-registration",
        "wall-clock",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/concurrent-gating-draws-soft-terms-2026-08-21.md"
    },
    {
      "entry_id": "bug/build-errors/concurrent-loop-skill-prose-linear-2026-08-22",
      "title": "Concurrent-loop skill prose: linear checklist + non-blocking claims contradict",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md",
      "tags": [
        "fn-203",
        "work-rolling",
        "scheduler",
        "event-driven",
        "plan-sync-barrier",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-22",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/concurrent-loop-skill-prose-linear-2026-08-22.md"
    },
    {
      "entry_id": "bug/build-errors/delegating-cli-wrapper-inherits-2026-08-30",
      "title": "Delegating CLI wrapper inherits delegate guards, prints, truncation, races",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-212",
        "memory-upsert",
        "delegation",
        "codex-review",
        "review-feedback",
        "concurrency"
      ],
      "date": "2026-08-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/delegating-cli-wrapper-inherits-2026-08-30.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/detectvalidate-must-require-specs-dir-2026-05-08.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/docs-activation-command-for-string-enum-2026-06-05.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/embedded-self-check-greps-in-reference-2026-06-12.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/env-marker-gate-must-scan-the-namespace-2026-06-04.md"
    },
    {
      "entry_id": "bug/build-errors/eval-ledger-feature-rows-must-disclaim-2026-07-18",
      "title": "Eval-ledger feature rows must disclaim the optimization ratchet + reconcile deno",
      "track": "bug",
      "category": "build-errors",
      "module": "optimization/interview",
      "tags": [
        "fn-100",
        "eval-ledger",
        "ratchet",
        "denominator-reconciliation",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-07-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/eval-ledger-feature-rows-must-disclaim-2026-07-18.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/fn-44-review-cycle-lessons-2026-05-21.md"
    },
    {
      "entry_id": "bug/build-errors/grep-c-prints-0-and-exits-1-echo-0-2026-07-24",
      "title": "grep -c prints 0 AND exits 1: || echo 0 yields a two-line count",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-audit/workflow.md",
      "tags": [
        "bash",
        "skill-prose",
        "grep",
        "shell-pitfall"
      ],
      "date": "2026-07-24",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/grep-c-prints-0-and-exits-1-echo-0-2026-07-24.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03.md"
    },
    {
      "entry_id": "bug/build-errors/implementer-brief-widened-never-list-2026-09-14",
      "title": "Implementer brief widened never-list past the spec; child lost its fan-out",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/templates/usage.md",
      "tags": [
        "fn-245",
        "fn-244",
        "bridge",
        "long-task-brief",
        "never-list",
        "delegation",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-09-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/implementer-brief-widened-never-list-2026-09-14.md"
    },
    {
      "entry_id": "bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12",
      "title": "Lavish interactive-only gate must check MODE var AND env markers in-snippet",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-capture/references/html-lens.md",
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/lavish-interactive-only-gate-must-check-2026-06-12.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11.md"
    },
    {
      "entry_id": "bug/build-errors/optional-side-effect-snippets-need-2026-06-12",
      "title": "Optional side-effect snippets need guarded git steps; check-ignore the exact fil",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-make-pr/html-lens.md",
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/optional-side-effect-snippets-need-2026-06-12.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/policy-claim-inversion-sweep-all-2026-06-18.md"
    },
    {
      "entry_id": "bug/build-errors/prose-tick-lock-claim-before-read-2026-08-28",
      "title": "Prose tick lock: claim before read, serialized reap, liveness refresh, persisted",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-208",
        "land",
        "concurrency",
        "ledger",
        "skill-prose",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/prose-tick-lock-claim-before-read-2026-08-28.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/r2-ask-block-mis-injected-into-negation-2026-06-27.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/scout-fallback-prose-drifted-from-specs-2026-05-26.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/sed-piped-default-masks-empty-source-2026-06-05.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-adding-version-bump-leaves-stale-2026-06-05.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-bash-set-arguments-cant-honor-2026-05-26.md"
    },
    {
      "entry_id": "bug/build-errors/skill-flag-gating-a-durable-write-needs-2026-08-31",
      "title": "Skill flag gating a durable write needs exact-token parse, not substring",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-capture/SKILL.md",
      "tags": [
        "fn-214",
        "skill-bash",
        "argument-parsing",
        "capture",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-31",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-flag-gating-a-durable-write-needs-2026-08-31.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/skill-workflow-snippets-must-enforce-2026-06-11.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/status-policy-map-needs-a-matching-2026-06-18.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/template-rewrite-env-var-cascade-2026-05-09.md"
    },
    {
      "entry_id": "bug/build-errors/unit-rename-substitution-broke-trigger-2026-07-18",
      "title": "Unit-rename substitution broke trigger thresholds (turns->rounds, fn-100)",
      "track": "bug",
      "category": "build-errors",
      "module": "plugins/flow-next/skills/flow-next-interview/references/doc-aware.md",
      "tags": [
        "interview",
        "rounds",
        "doc-aware",
        "thresholds",
        "spec-contract",
        "impl-review",
        "fn-100"
      ],
      "date": "2026-07-18",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/unit-rename-substitution-broke-trigger-2026-07-18.md"
    },
    {
      "entry_id": "bug/build-errors/verdict-tasks-must-rewrite-not-banner-a-2026-07-03",
      "title": "Verdict tasks must rewrite, not banner, a sibling task's flipped scope",
      "track": "bug",
      "category": "build-errors",
      "module": ".flow/tasks",
      "tags": [
        "fn-83",
        "plan-sync-gate",
        "task-marking",
        "verdict",
        "workflow"
      ],
      "date": "2026-07-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/build-errors/verdict-tasks-must-rewrite-not-banner-a-2026-07-03.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/archaeology-fn-strip-can-over-strip-a-2026-07-02.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/final-gate-grep-for-a-forbidden-token-2026-07-02.md"
    },
    {
      "entry_id": "bug/test-failures/flag-substring-assertion-passes-when-a-2026-09-23",
      "title": "Flag substring assertion passes when a longer sibling flag is present",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/test_spec_id_routing_prose.py",
      "tags": [
        "prose-test",
        "cli-flags",
        "false-green"
      ],
      "date": "2026-09-23",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/flag-substring-assertion-passes-when-a-2026-09-23.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/rename-smoke-rewire-variable-form-cli-2026-05-09.md"
    },
    {
      "entry_id": "bug/test-failures/test-asserted-a-public-envelope-that-2026-08-01",
      "title": "Test asserted a public envelope that never carried the field",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/test_chart_briefing.py",
      "tags": [
        "chart",
        "test-design",
        "review-feedback",
        "api-surface",
        "scope"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-asserted-a-public-envelope-that-2026-08-01.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-fixtures-must-mirror-upstream-zod-2026-05-26.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-production-path-not-parallel-construction-2026-05-21.md"
    },
    {
      "entry_id": "bug/test-failures/test-runner-timeout-must-kill-a-process-2026-08-04",
      "title": "Test-runner timeout must kill a process TREE whose identity outlives the shard",
      "track": "bug",
      "category": "test-failures",
      "module": "scripts/run_tests_parallel.py",
      "tags": [
        "windows",
        "subprocess",
        "process-group",
        "job-object",
        "timeout",
        "ci",
        "test-runner"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/test-runner-timeout-must-kill-a-process-2026-08-04.md"
    },
    {
      "entry_id": "bug/test-failures/two-independent-resolve-calls-faked-a-2026-08-04",
      "title": "Two independent resolve() calls faked a path escape on Windows",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py",
      "tags": [
        "windows",
        "flake",
        "path-safety",
        "tracker",
        "concurrency"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/two-independent-resolve-calls-faked-a-2026-08-04.md"
    },
    {
      "entry_id": "bug/test-failures/windows-83-path-test-failures-were-2026-08-04",
      "title": "Windows '8.3 path' test failures were cp1252 fixtures + unguarded geteuid",
      "track": "bug",
      "category": "test-failures",
      "module": "plugins/flow-next/tests/test_normalize_section_content.py",
      "tags": [
        "fn-120",
        "windows",
        "encoding",
        "cp1252",
        "utf-8",
        "8.3-short-path",
        "geteuid",
        "skipif",
        "json-stdout"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/test-failures/windows-83-path-test-failures-were-2026-08-04.md"
    },
    {
      "entry_id": "bug/runtime-errors/bash-deadline-watchdogs-orphaned-sleep-2026-07-16",
      "title": "Bash deadline watchdogs: orphaned sleep holds pipes; group-kill via setsid, not ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "agent_docs/guidance-eval/runner.sh",
      "tags": [
        "bash",
        "timeout",
        "process-group",
        "setsid",
        "watchdog",
        "eval-harness",
        "fn-99"
      ],
      "date": "2026-07-16",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/bash-deadline-watchdogs-orphaned-sleep-2026-07-16.md"
    },
    {
      "entry_id": "bug/runtime-errors/empty-value-semantics-leak-null-in-2026-07-20",
      "title": "Empty-value semantics leak: {} -> null in snapshot config reads; empty file -> T",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "config-snapshot",
        "empty-values",
        "truthiness",
        "fn-110"
      ],
      "date": "2026-07-20",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/empty-value-semantics-leak-null-in-2026-07-20.md"
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
        "review-feedback",
        "fn-102",
        "gate-diet",
        "path-normalization",
        "fail-open",
        "codex-review"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/flowctl-on-disk-per-key-counter-count-2026-06-27.md"
    },
    {
      "entry_id": "bug/runtime-errors/forced-color-git-grep-output-defeats-2026-07-19",
      "title": "Forced-color git grep output defeats regex post-filter (SGR escapes)",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "git",
        "subprocess",
        "regex",
        "export",
        "ansi"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/forced-color-git-grep-output-defeats-2026-07-19.md"
    },
    {
      "entry_id": "bug/runtime-errors/glob-walk-file-loads-need-lstat-screen-2026-07-19",
      "title": "Glob-walk file loads need lstat screen + RecursionError; revalidate TTL post-sta",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "gate",
        "green-receipt",
        "fail-closed",
        "fifo",
        "json"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/glob-walk-file-loads-need-lstat-screen-2026-07-19.md"
    },
    {
      "entry_id": "bug/runtime-errors/land-chain-fences-a-failed-read-is-2026-09-13",
      "title": "Land chain fences: a failed read is never permission; write multi-layer records ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-149",
        "land",
        "chains",
        "stacks",
        "cascade",
        "skill-prose",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-09-13",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/land-chain-fences-a-failed-read-is-2026-09-13.md"
    },
    {
      "entry_id": "bug/runtime-errors/one-shot-keyed-to-an-earlier-captured-2026-08-19",
      "title": "One-shot keyed to an earlier-captured SHA: re-validate after the claim, release ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "fn-200",
        "land",
        "one-shot",
        "concurrency",
        "claim-dir",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-08-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/one-shot-keyed-to-an-earlier-captured-2026-08-19.md"
    },
    {
      "entry_id": "bug/runtime-errors/same-owner-alias-re-registration-must-2026-08-02",
      "title": "Same-owner alias re-registration must harden a weak claim, not no-op",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "chart",
        "aliases",
        "two-pass-validation",
        "flowctl"
      ],
      "date": "2026-08-02",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/same-owner-alias-re-registration-must-2026-08-02.md"
    },
    {
      "entry_id": "bug/runtime-errors/skill-fences-that-degrade-only-without-2026-09-13",
      "title": "Skill fences that degrade only without set -e: masked failures in make-pr chain ",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md",
      "tags": [
        "set-e",
        "bash-fence",
        "fixtures",
        "make-pr",
        "chain",
        "stack"
      ],
      "date": "2026-09-13",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/skill-fences-that-degrade-only-without-2026-09-13.md"
    },
    {
      "entry_id": "bug/runtime-errors/structured-review-parsers-must-2026-07-30",
      "title": "Structured review parsers must distinguish invalid from absent",
      "track": "bug",
      "category": "runtime-errors",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-136",
        "review-findings",
        "fail-closed",
        "parser",
        "impl-review"
      ],
      "date": "2026-07-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/structured-review-parsers-must-2026-07-30.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/runtime-errors/who-wins-ladder-must-check-the-2026-06-03.md"
    },
    {
      "entry_id": "bug/performance/linear-graphql-every-nodes-connection-2026-06-03",
      "title": "Linear GraphQL: every {nodes} connection needs first: \u2014 incl. workflowStates/tea",
      "track": "bug",
      "category": "performance",
      "module": "plugins/flow-next/scripts/flowctl_tracker/wire/linear.py",
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/performance/linear-graphql-every-nodes-connection-2026-06-03.md"
    },
    {
      "entry_id": "bug/security/guard-matcher-narrowing-missed-shell-2026-09-25",
      "title": "Guard matcher narrowing missed shell control words and split redirect words",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/hooks/ralph-guard.py",
      "tags": [
        "ralph-guard",
        "shell-parsing",
        "bypass"
      ],
      "date": "2026-09-25",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/guard-matcher-narrowing-missed-shell-2026-09-25.md"
    },
    {
      "entry_id": "bug/security/managed-review-transport-must-bound-2026-09-08",
      "title": "Managed review transport must bound time and protect scoped credentials",
      "track": "bug",
      "category": "security",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "managed-review",
        "transport",
        "credentials"
      ],
      "date": "2026-09-08",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/managed-review-transport-must-bound-2026-09-08.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/rollback-path-sanitizer-must-not-2026-06-05.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/security/shell-command-allowlist-gates-must-2026-06-05.md"
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
        "fn-74",
        "claude",
        "fn-221"
      ],
      "date": "2026-06-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/adding-a-review-backend-sweep-all-2026-06-29.md"
    },
    {
      "entry_id": "bug/integration/backend-special-case-in-a-shared-helper-2026-09-05",
      "title": "Backend special-case in a shared helper is an enumeration site too",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review-backend",
        "claude",
        "enumeration-sweep",
        "fn-221",
        "tracker-manifest"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/backend-special-case-in-a-shared-helper-2026-09-05.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/byte-for-byte-spec-contract-branch-2026-07-01.md"
    },
    {
      "entry_id": "bug/integration/caller-facade-guards-must-cover-retro-2026-07-29",
      "title": "Caller facade guards must cover retro-fire paths",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-capture/workflow.md",
      "tags": [
        "fn-141",
        "tracker-sync",
        "facade",
        "retro-fire",
        "oracle"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/caller-facade-guards-must-cover-retro-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/caller-fakes-must-enforce-lifecycle-2026-07-29",
      "title": "Caller fakes must enforce lifecycle facade input contracts",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/tests/test_tracker_caller_execution.py",
      "tags": [
        "fn-141",
        "tracker-sync",
        "caller-harness",
        "facade",
        "impl-review"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/caller-fakes-must-enforce-lifecycle-2026-07-29.md"
    },
    {
      "entry_id": "bug/integration/caller-oracle-must-preserve-historical-2026-07-29",
      "title": "Caller oracle must preserve historical quirks and exact observations",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/tests/test_tracker_caller_oracle.py",
      "tags": [
        "fn-141",
        "tracker-sync",
        "oracle",
        "impl-review"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/caller-oracle-must-preserve-historical-2026-07-29.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/ceremony-validation-must-read-persisted-2026-06-28.md"
    },
    {
      "entry_id": "bug/integration/ci-path-classification-must-include-2026-09-05",
      "title": "CI path classification must include rename sources",
      "track": "bug",
      "category": "integration",
      "module": "scripts/ci/classify_changes.py",
      "tags": [
        "ci",
        "git",
        "renames",
        "path-classification"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/ci-path-classification-must-include-2026-09-05.md"
    },
    {
      "entry_id": "bug/integration/claude-p-clean-room-on-oauth-logins-2026-07-16",
      "title": "claude -p clean-room on OAuth logins: --setting-sources project,local; --bare an",
      "track": "bug",
      "category": "integration",
      "module": "agent_docs/guidance-eval/runner.sh",
      "tags": [
        "claude-cli",
        "clean-room",
        "eval-harness",
        "oauth",
        "setting-sources",
        "bare",
        "fn-99"
      ],
      "date": "2026-07-16",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/claude-p-clean-room-on-oauth-logins-2026-07-16.md"
    },
    {
      "entry_id": "bug/integration/cross-family-review-claims-key-on-the-2026-09-05",
      "title": "Cross-family review claims key on the writer's model family, never the host name",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/docs",
      "tags": [
        "review-backend",
        "claude",
        "cross-family",
        "docs",
        "fn-221"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/cross-family-review-claims-key-on-the-2026-09-05.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/drop-receipt-to-break-codex-2026-05-09.md"
    },
    {
      "entry_id": "bug/integration/forwarded-license-carried-the-wrong-2026-09-14",
      "title": "Forwarded license carried the wrong holder's commit contract into the bridged ch",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/agents/worker.md",
      "tags": [
        "fn-245",
        "bridge",
        "worker",
        "phase-1b",
        "license",
        "dispatch-field",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-09-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/forwarded-license-carried-the-wrong-2026-09-14.md"
    },
    {
      "entry_id": "bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17",
      "title": "gh api -f stringifies numeric body fields (issue_id) \u2192 GitHub 422; use -F",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl_tracker/",
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/gh-api-f-stringifies-numeric-body-2026-06-17.md"
    },
    {
      "entry_id": "bug/integration/head-bound-html-artifacts-must-not-2026-07-30",
      "title": "Head-bound HTML artifacts must not stale their own input",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-make-pr/html-lens.md",
      "tags": [
        "fn-136",
        "make-pr",
        "html",
        "currentness",
        "semantic-carrier",
        "impl-review"
      ],
      "date": "2026-07-30",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/head-bound-html-artifacts-must-not-2026-07-30.md"
    },
    {
      "entry_id": "bug/integration/headless-review-backend-error-envelope-2026-09-05",
      "title": "Headless review backend: error-envelope text must never ride the output slot",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "review-backend",
        "claude",
        "transport",
        "verdict-channel",
        "fn-221"
      ],
      "date": "2026-09-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/headless-review-backend-error-envelope-2026-09-05.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/heredoc-built-json-breaks-on-free-form-2026-06-05.md"
    },
    {
      "entry_id": "bug/integration/installer-must-own-what-it-deletes-2026-08-21",
      "title": "",
      "track": "bug",
      "category": "integration",
      "module": "scripts/install-codex.sh, scripts/sync-codex.sh",
      "tags": [
        "installer",
        "ownership",
        "namespace",
        "data-loss",
        "codex",
        "mirror"
      ],
      "date": "2026-08-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/installer-must-own-what-it-deletes-2026-08-21.md"
    },
    {
      "entry_id": "bug/integration/land-evidence-field-defaulted-to-off-on-2026-08-19",
      "title": "land evidence field defaulted to 'off' on configured-but-not-due paths",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-land/workflow.md",
      "tags": [
        "land",
        "evidence",
        "report-vocabulary"
      ],
      "date": "2026-08-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/land-evidence-field-defaulted-to-off-on-2026-08-19.md"
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
        "cross-model-review",
        "fn-141",
        "facade",
        "comments",
        "prose-teardown"
      ],
      "date": "2026-06-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/markerstruct-field-semantics-must-2026-06-27.md"
    },
    {
      "entry_id": "bug/integration/path-handoff-template-id-slots-must-use-2026-07-19",
      "title": "Path-handoff template id slots must use canonical ids, not aliases",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-work/references/codex-delegation.md",
      "tags": [
        "fn-103",
        "codex-delegation",
        "path-handoff",
        "alias-resolution",
        "prose-contract",
        "review-feedback"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/path-handoff-template-id-slots-must-use-2026-07-19.md"
    },
    {
      "entry_id": "bug/integration/plan-review-criteria-edits-must-also-2026-09-14",
      "title": "Plan-review criteria edits must also sweep workflow-rp.md (CE summary + Classic ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md",
      "tags": [
        "plan-review",
        "repoprompt",
        "prompt-pins",
        "codex-review"
      ],
      "date": "2026-09-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/plan-review-criteria-edits-must-also-2026-09-14.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/rp-builder-file-slices-cause-false-2026-06-10.md"
    },
    {
      "entry_id": "bug/integration/scheduler-prose-asserted-wrong-config-2026-08-22",
      "title": "Scheduler prose asserted wrong config default; slot-hold drain rules deadlock",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md",
      "tags": [
        "fn-203",
        "work-rolling",
        "planSync",
        "config-defaults",
        "deadlock",
        "skill-prose"
      ],
      "date": "2026-08-22",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/scheduler-prose-asserted-wrong-config-2026-08-22.md"
    },
    {
      "entry_id": "bug/integration/set-tracker-id-rejected-github-n-2026-06-03",
      "title": "set-tracker-id rejected GitHub #N identifiers (Linear-only handle validator)",
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/skill-bash-blocks-re-declare-every-2026-07-02.md"
    },
    {
      "entry_id": "bug/integration/skill-fence-consolidation-6-contract-2026-07-20",
      "title": "Skill-fence consolidation: 6 contract regressions (var-atomicity, symlink, dry-r",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills",
      "tags": [
        "skill-prose",
        "fences",
        "dry-run",
        "symlink-safety",
        "fn-110"
      ],
      "date": "2026-07-20",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/skill-fence-consolidation-6-contract-2026-07-20.md"
    },
    {
      "entry_id": "bug/integration/spec-named-config-keys-must-be-checked-2026-07-15",
      "title": "Spec-named config keys must be checked against shipped surface; cross-family is",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-setup/workflow.md",
      "tags": [
        "fn-97",
        "config-contract",
        "spec-amendment",
        "cross-family-review",
        "codex-review",
        "review-feedback"
      ],
      "date": "2026-07-15",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/spec-named-config-keys-must-be-checked-2026-07-15.md"
    },
    {
      "entry_id": "bug/integration/summary-sinks-for-repeatable-mixed-2026-07-19",
      "title": "Summary sinks for repeatable mixed-outcome events need per-event lines, not one ",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/skills/flow-next-work/phases.md",
      "tags": [
        "prose-contract",
        "summary-template",
        "gate-diet",
        "fn-102",
        "review-finding"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/summary-sinks-for-repeatable-mixed-2026-07-19.md"
    },
    {
      "entry_id": "bug/integration/tracker-ownership-rewrites-require-2026-07-29",
      "title": "Tracker ownership rewrites require adjacent fidelity sweeps",
      "track": "bug",
      "category": "integration",
      "module": "plugins/flow-next/docs/tracker-sync.md",
      "tags": [
        "fn-141",
        "tracker-sync",
        "docs-contract",
        "provider-fidelity",
        "impl-review"
      ],
      "date": "2026-07-29",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/tracker-ownership-rewrites-require-2026-07-29.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/integration/trackers-auto-linkify-issue-key-2026-06-03.md"
    },
    {
      "entry_id": "bug/data/adding-a-key-to-a-content-hash-orphans-2026-08-01",
      "title": "Adding a key to a content hash orphans records the old binary wrote",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fingerprint",
        "idempotence",
        "upgrade-compat",
        "golden-fixture",
        "chart"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/adding-a-key-to-a-content-hash-orphans-2026-08-01.md"
    },
    {
      "entry_id": "bug/data/docs-for-a-hash-identity-fix-inherit-2026-08-01",
      "title": "Docs for a hash-identity fix inherit the hash's precision",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/docs/flowctl.md",
      "tags": [
        "chart",
        "fingerprint",
        "changelog",
        "docs-pin",
        "review-feedback"
      ],
      "date": "2026-08-01",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/docs-for-a-hash-identity-fix-inherit-2026-08-01.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/fence-preserving-writer-needs-fence-2026-07-02.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/migrationrollback-cli-10-review-cycle-2026-05-08.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/paired-snapshot-setter-must-write-both-2026-06-03.md"
    },
    {
      "entry_id": "bug/data/relaxing-a-validator-must-only-admit-2026-09-26",
      "title": "Relaxing a validator must only admit values the writer round-trips",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-257",
        "memory",
        "frontmatter",
        "validation",
        "round-trip"
      ],
      "date": "2026-09-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/relaxing-a-validator-must-only-admit-2026-09-26.md"
    },
    {
      "entry_id": "bug/data/yaml-frontmatter-writer-unescaped-2026-07-24",
      "title": "YAML frontmatter writer: unescaped newlines lose the entry; frontmatter-only wri",
      "track": "bug",
      "category": "data",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "memory",
        "yaml",
        "frontmatter",
        "round-trip"
      ],
      "date": "2026-07-24",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/data/yaml-frontmatter-writer-unescaped-2026-07-24.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/bug/ui/flow-nextdev-docs-page-needs-2026-06-03.md"
    },
    {
      "entry_id": "knowledge/conventions/unattended-detection-uses-the-full-2026-09-26",
      "title": "Unattended detection uses the full autonomy marker namespace",
      "track": "knowledge",
      "category": "conventions",
      "module": "skills",
      "tags": [
        "autonomy",
        "mode:autonomous",
        "tracker-sync",
        "flow-auto",
        "defer"
      ],
      "date": "2026-09-26",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/conventions/unattended-detection-uses-the-full-2026-09-26.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/final-integration-tasks-need-wider-impl-2026-05-26.md"
    },
    {
      "entry_id": "knowledge/workflow/github-rulesets-need-an-admin-bypass-or-2026-09-11",
      "title": "GitHub rulesets need an admin bypass or spec-only commits stall",
      "track": "knowledge",
      "category": "workflow",
      "module": "ci",
      "tags": [
        "github",
        "rulesets",
        "ci",
        "flow-state"
      ],
      "date": "2026-09-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/github-rulesets-need-an-admin-bypass-or-2026-09-11.md"
    },
    {
      "entry_id": "knowledge/workflow/harness-capability-claims-verify-at-the-2026-08-28",
      "title": "Harness capability claims: verify at the installer, not the generator",
      "track": "knowledge",
      "category": "workflow",
      "module": "platforms",
      "tags": [
        "scouts",
        "opencode",
        "installers",
        "negative-claims"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/harness-capability-claims-verify-at-the-2026-08-28.md"
    },
    {
      "entry_id": "knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04",
      "title": "",
      "track": "knowledge",
      "category": "workflow",
      "module": "review-subsystem",
      "tags": [
        "bot-review",
        "land",
        "convergence",
        "triage",
        "severity-inflation"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04.md"
    },
    {
      "entry_id": "knowledge/workflow/split-pr-at-second-adjacent-surface-finding-2026-08-21",
      "title": "",
      "track": "knowledge",
      "category": "workflow",
      "module": "review",
      "tags": [
        "resolve-pr",
        "land",
        "scope",
        "review-rounds",
        "pr-hygiene"
      ],
      "date": "2026-08-21",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/split-pr-at-second-adjacent-surface-finding-2026-08-21.md"
    },
    {
      "entry_id": "knowledge/workflow/stacked-pr-squash-close-recovery-2026-08-27",
      "title": "Squash-merging a stacked PR's base permanently closes the stacked PR - rebase + successor PR is the recovery",
      "track": "knowledge",
      "category": "workflow",
      "module": "land",
      "tags": [
        "stacked-prs",
        "squash-merge",
        "land",
        "gh",
        "rebase",
        "delete-branch",
        "github-behavior"
      ],
      "date": "2026-08-27",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/workflow/stacked-pr-squash-close-recovery-2026-08-27.md"
    },
    {
      "entry_id": "knowledge/best-practices/failures-after-a-restart-suspect-2026-08-28",
      "title": "Failures after a restart: suspect persistent state before code",
      "track": "knowledge",
      "category": "best-practices",
      "module": ".flow",
      "tags": [
        "fn-208",
        "debugging",
        "persistent-state",
        "state-validation"
      ],
      "date": "2026-08-28",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/best-practices/failures-after-a-restart-suspect-2026-08-28.md"
    },
    {
      "entry_id": "knowledge/best-practices/scb-benchmark-proof-fn-163164-2026-08-04",
      "title": "SCB benchmark proof: fn-163/164 eliminated ceremony as a cost factor",
      "track": "knowledge",
      "category": "best-practices",
      "module": "",
      "tags": [
        "fn-163",
        "fn-164",
        "fn-165",
        "slopcodebench",
        "benchmark"
      ],
      "date": "2026-08-04",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/best-practices/scb-benchmark-proof-fn-163164-2026-08-04.md"
    },
    {
      "entry_id": "knowledge/best-practices/windows-path-shims-cannot-observe-2026-08-11",
      "title": "Windows PATH shims cannot observe subprocess spawns (CreateProcess skips PATHEXT",
      "track": "knowledge",
      "category": "best-practices",
      "module": "plugins/flow-next/tests",
      "tags": [
        "windows",
        "ci",
        "subprocess",
        "spawn-count",
        "git-shim"
      ],
      "date": "2026-08-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/best-practices/windows-path-shims-cannot-observe-2026-08-11.md"
    },
    {
      "entry_id": "knowledge/decisions/bugbot-pre-push-stage-wont-do-patch-id-2026-08-07",
      "title": "Bugbot pre-push stage: won't-do - patch-ID dedup falsified live",
      "track": "knowledge",
      "category": "decisions",
      "module": "review",
      "tags": [
        "bugbot",
        "cursor",
        "review-backends"
      ],
      "date": "2026-08-07",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/bugbot-pre-push-stage-wont-do-patch-id-2026-08-07.md"
    },
    {
      "entry_id": "knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19",
      "title": "Composed brief deleted: path-handoff replaces it (fn-103 eval)",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/skills/flow-next-work/references/codex-delegation.md",
      "tags": [
        "fn-103",
        "codex-delegation",
        "path-handoff",
        "eval",
        "delegation",
        "bitter-lesson"
      ],
      "date": "2026-07-19",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/factory-droid-platform-status-2026-05-2026-05-25.md"
    },
    {
      "entry_id": "knowledge/decisions/pilot-strike-recovery-is-a-cli-verb-not-2026-08-11",
      "title": "Pilot strike recovery is a CLI verb, not board-native transition detection",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/skills/flow-next-pilot",
      "tags": [
        "pilot",
        "strikes",
        "tracker-sync",
        "readyState",
        "fn-184"
      ],
      "date": "2026-08-11",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/pilot-strike-recovery-is-a-cli-verb-not-2026-08-11.md"
    },
    {
      "entry_id": "knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03",
      "title": "A deterministic plan-sync skip-gate is not viable \u2014 do not re-attempt",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/skills/flow-next-work/phases.md",
      "tags": [
        "plan-sync",
        "work-loop",
        "gate",
        "eval",
        "fn-83",
        "drift",
        "determinism",
        "shelved"
      ],
      "date": "2026-07-03",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md"
    },
    {
      "entry_id": "knowledge/decisions/ralph-guard-reverts-its-delegation-2026-08-14",
      "title": "Ralph guard reverts its delegation amendment; bridge safety is prose-only",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/scripts/hooks/ralph-guard.py",
      "tags": [
        "flow-98",
        "ralph-guard",
        "codex-delegation",
        "safety",
        "deprecation"
      ],
      "date": "2026-08-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/ralph-guard-reverts-its-delegation-2026-08-14.md"
    },
    {
      "entry_id": "knowledge/decisions/review-stall-detection-reads-resolution-2026-08-05",
      "title": "Review stall detection reads resolution; the trend heuristics are deleted (fn-168)",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "fn-168",
        "fn-159",
        "review-convergence",
        "stall-detection",
        "ratchet-prompt",
        "findings-lineage",
        "inference-vs-evidence"
      ],
      "date": "2026-08-05",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/review-stall-detection-reads-resolution-2026-08-05.md"
    },
    {
      "entry_id": "knowledge/decisions/tracked-vs-runtime-durability-contract-2026-08-14",
      "title": "Tracked-vs-runtime durability contract - done crosses it, validate respects it",
      "track": "knowledge",
      "category": "decisions",
      "module": "plugins/flow-next/scripts/flowctl.py",
      "tags": [
        "durability",
        "flow-state",
        "status-source",
        "validate",
        "fn-192"
      ],
      "date": "2026-08-14",
      "status": "active",
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/tracked-vs-runtime-durability-contract-2026-08-14.md"
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
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/.flow/memory/knowledge/decisions/tracker-sync-is-projection-not-2026-06-01.md"
    }
  ],
  "legacy": [],
  "count": 118,
  "status": "active"
}

===== [11/11] dependencies: ids, titles, statuses, done summaries =====
- fn-64-tracker-sync-project-flow-spec.2 [todo] - Adapter interface contract: setIssueRelation / listIssueRelations + relation struct
    Documented the normalized dependency-relation contract in adapter-interface.md: added `setIssueRelation(issue, blockedBy)` / `listIssueRelations(issue)` to the transport table, a new `relation` struct `{from, to, type, source}`, the once-stated blocked-by direction convention, and the mandatory read-before-write idempotency + never-delete-non-ours provenance rules — cross-linked to fn-64.1's depRelations ledger and the fn-64.4 fenced-block/body-merge exclusion. Contract-only doc that unblocks fn-64.3 and fn-64.4.

