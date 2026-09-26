# Worker anchor bundle - fn-64-tracker-sync-project-flow-spec.3 (spec fn-64-tracker-sync-project-flow-spec)

Each section is the verbatim output of the command it is labeled with, in fixed order, untruncated. The bundle is a floor, not a ceiling - memory keyword-search and every further read remain available.

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

===== [5/11] git_status: `git status --short --branch` =====
## fn-258-smaller-default-outputs-and-bundles...origin/main [ahead 1]
 M agent_docs/adding-skills.md
 M optimization/worker-anchor/run_eval.py
 M plugins/flow-next/agents/repo-scout.md
 M plugins/flow-next/agents/spec-scout.md
 M plugins/flow-next/agents/worker.md
 M plugins/flow-next/codex/agents/repo-scout.toml
 M plugins/flow-next/codex/agents/spec-scout.toml
 M plugins/flow-next/codex/agents/worker.toml
 M plugins/flow-next/codex/docs/flow-next/flowctl.md
 M plugins/flow-next/codex/docs/flow-next/glossary.md
 M plugins/flow-next/codex/skills/flow-next-capture/workflow.md
 M plugins/flow-next/codex/skills/flow-next-features/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-impl-review/workflow-codex.md
 M plugins/flow-next/codex/skills/flow-next-impl-review/workflow-host.md
 M plugins/flow-next/codex/skills/flow-next-impl-review/workflow-rp.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-claude.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-codex.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-copilot.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-cursor.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-host.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow-rp.md
 M plugins/flow-next/codex/skills/flow-next-plan-review/workflow.md
 M plugins/flow-next/codex/skills/flow-next-plan/references/selected-review.md
 M plugins/flow-next/codex/skills/flow-next-refine/references/pass-business.md
 M plugins/flow-next/codex/skills/flow-next-resolve-pr/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-resolve-pr/workflow.md
 M plugins/flow-next/codex/skills/flow-next-setup/templates/agents-md-snippet.md
 M plugins/flow-next/codex/skills/flow-next-setup/templates/claude-md-snippet.md
 M plugins/flow-next/codex/skills/flow-next-setup/workflow.md
 M plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-host.md
 M plugins/flow-next/codex/skills/flow-next-spec-completion-review/workflow-rp.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/adapter-interface.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/body-merge.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/comments-sync.md
 M plugins/flow-next/codex/skills/flow-next-tracker-sync/references/status-sync.md
 M plugins/flow-next/codex/skills/flow-next-work/SKILL.md
 M plugins/flow-next/codex/skills/flow-next-work/phases.md
 M plugins/flow-next/codex/skills/flow-next-work/references/host-deferred-review.md
 M plugins/flow-next/codex/skills/flow-next/SKILL.md
 M plugins/flow-next/commands/audit.md
 M plugins/flow-next/commands/capture.md
 M plugins/flow-next/commands/chart.md
 M plugins/flow-next/commands/features.md
 M plugins/flow-next/commands/flow.md
 M plugins/flow-next/commands/impl-review.md
 M plugins/flow-next/commands/land.md
 M plugins/flow-next/commands/make-pr.md
 M plugins/flow-next/commands/map.md
 M plugins/flow-next/commands/memory-migrate.md
 M plugins/flow-next/commands/plan-review.md
 M plugins/flow-next/commands/plan.md
 M plugins/flow-next/commands/prime.md
 M plugins/flow-next/commands/prose.md
 M plugins/flow-next/commands/prospect.md
 M plugins/flow-next/commands/qa.md
 M plugins/flow-next/commands/ralph-init.md
 M plugins/flow-next/commands/refine.md
 M plugins/flow-next/commands/resolve-pr.md
 M plugins/flow-next/commands/setup.md
 M plugins/flow-next/commands/spec-completion-review.md
 M plugins/flow-next/commands/strategy.md
 M plugins/flow-next/commands/sync.md
 M plugins/flow-next/commands/tracker-sync.md
 M plugins/flow-next/commands/uninstall.md
 M plugins/flow-next/commands/visual.md
 M plugins/flow-next/commands/work.md
 M plugins/flow-next/docs/flowctl.md
 M plugins/flow-next/docs/glossary.md
 M plugins/flow-next/scripts/flowctl.py
 M plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json
 M plugins/flow-next/skills/flow-next-capture/workflow.md
 M plugins/flow-next/skills/flow-next-features/SKILL.md
 M plugins/flow-next/skills/flow-next-flow/auto.md
 M plugins/flow-next/skills/flow-next-flow/references/backlog-mode.md
 M plugins/flow-next/skills/flow-next-flow/references/gate-selection.md
 M plugins/flow-next/skills/flow-next-flow/references/plan-vs-no-plan.md
 M plugins/flow-next/skills/flow-next-flow/references/route-matrix.md
 M plugins/flow-next/skills/flow-next-flow/references/tail.md
 M plugins/flow-next/skills/flow-next-flow/workflow.md
 M plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md
 M plugins/flow-next/skills/flow-next-impl-review/workflow-host.md
 M plugins/flow-next/skills/flow-next-impl-review/workflow-rp.md
 M plugins/flow-next/skills/flow-next-plan-review/SKILL.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-claude.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-codex.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-copilot.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-cursor.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-host.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md
 M plugins/flow-next/skills/flow-next-plan-review/workflow.md
 M plugins/flow-next/skills/flow-next-plan/references/selected-review.md
 M plugins/flow-next/skills/flow-next-refine/SKILL.md
 M plugins/flow-next/skills/flow-next-refine/references/pass-business.md
 M plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md
 M plugins/flow-next/skills/flow-next-resolve-pr/workflow.md
 M plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md
 M plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md
 M plugins/flow-next/skills/flow-next-setup/workflow.md
 M plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md
 M plugins/flow-next/skills/flow-next-spec-completion-review/workflow-rp.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md
 M plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md
 M plugins/flow-next/skills/flow-next-work/SKILL.md
 M plugins/flow-next/skills/flow-next-work/phases.md
 M plugins/flow-next/skills/flow-next-work/references/host-deferred-review.md
 M plugins/flow-next/skills/flow-next-work/references/rolling-scheduler.md
 M plugins/flow-next/skills/flow-next-work/references/wave-join.md
 M plugins/flow-next/skills/flow-next/SKILL.md
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-capture-brief.json
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-chart.json
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-route-interview.json
 M plugins/flow-next/tests/fixtures/chart_prompt_scenarios/flow-skip-chart-clear.json
 M plugins/flow-next/tests/test_anchor_bundle.py
 M plugins/flow-next/tests/test_flow_merge_destination.py
 M plugins/flow-next/tests/test_parallel_work_prose.py
 M plugins/flow-next/tests/test_pilot_chain_stages.py
 M plugins/flow-next/tests/test_precheck_mode_contract.py
 M plugins/flow-next/tests/test_review_convergence_cap.py
 M plugins/flow-next/tests/test_setup_snippet_lockstep.py
 M scripts/sync-codex.sh
?? optimization/worker-anchor/gen_fn258_inputs.py
?? optimization/worker-anchor/inputs/fn-64.3/bundle-current.md
?? plugins/flow-next/codex/skills/flow-next-tracker-sync/references/chart-subjects.md
?? plugins/flow-next/skills/flow-next-tracker-sync/references/chart-subjects.md
?? plugins/flow-next/tests/test_glossary_match.py
?? plugins/flow-next/tests/test_skill_id_invocations.py

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

===== [9/11] glossary: `flowctl glossary list --json --match "<task title + description>"` =====
{
  "success": true,
  "groups": [
    {
      "path": "/home/gordon/.cache/flow-next-wt/wt-258/GLOSSARY.md",
      "entries": [
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
        }
      ],
      "count": 2
    }
  ],
  "file_count": 1,
  "total_terms": 2
}

===== [10/11] memory_index: `flowctl memory list` =====
bug/build-errors/
  detectvalidate-must-require-specs-dir-2026-05-08 — "detect/validate must require SPECS_DIR even when EPICS_DIR present" (module: plugins/flow-next/scripts/flowctl.py)
  template-rewrite-env-var-cascade-2026-05-09 — "Env-var cascade in templates + canonical config.env knob alignment" (module: plugins/flow-next/skills/flow-next-ralph-init/templates, config.env, ralph.sh)
  abort-option-copy-must-reflect-pre-2026-05-18 — "Abort-option copy must reflect pre-prompt state mutations (idempotent != no chan" (module: plugins/flow-next/skills/flow-next-setup/workflow.md)
  codex-mirror-smoke-docs-miss-composed-2026-05-18 — "Codex mirror smoke docs miss composed transform output (abort + Other)" (module: agent_docs/local-dev.md)
  fn-44-review-cycle-lessons-2026-05-21 — "fn-44 review-cycle lessons (10+ NEEDS_WORK rounds across 4 tasks)" (module: plugins/flow-next/skills/flow-next-interview, plugins/flow-next/skills/flow-next-capture, plugins/flow-next/scripts/flowctl.py, scripts/sync-codex.sh, plugins/flow-next/templates/spec.md)
  scout-fallback-prose-drifted-from-specs-2026-05-26 — "Scout fallback prose drifted from spec's decision-lock command shape" (module: plugins/flow-next/agents/context-scout.md)
  skill-bash-set-arguments-cant-honor-2026-05-26 — "Skill bash `set -- $ARGUMENTS` can't honor 'verbatim' passthrough" (module: plugins/flow-next/skills/flow-next-map/workflow.md)
  id-grammar-widening-must-cover-the-full-2026-06-03 — "Id-grammar widening must cover the FULL command surface, not just named commands" (module: plugins/flow-next/scripts/flowctl.py)
  env-marker-gate-must-scan-the-namespace-2026-06-04 — "Env-marker gate must scan the namespace, not a fixed var list" (module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md)
  docs-activation-command-for-string-enum-2026-06-05 — "Docs activation command for string-enum config knob used bool true instead of th" (module: plugins/flow-next/docs/flowctl.md, .flow/usage.md)
  sed-piped-default-masks-empty-source-2026-06-05 — "sed-piped default masks empty source: || fallback never fires" (module: plugins/flow-next/skills/flow-next-qa/workflow.md)
  skill-adding-version-bump-leaves-stale-2026-06-05 — "Skill-adding version bump leaves stale skill/command counts in JSON manifest des" (module: plugins/flow-next/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/flow-next/.codex-plugin/plugin.json)
  mirror-regen-exposes-latent-canonical-2026-06-11 — "Mirror regen exposes latent canonical gaps: path rewrites, .flow persistence, di" (module: scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-land/workflow.md)
  skill-workflow-snippets-must-enforce-2026-06-11 — "Skill workflow snippets must enforce what the prose mandates (vars, gates, dispa" (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  embedded-self-check-greps-in-reference-2026-06-12 — "Embedded self-check greps in reference docs need POSIX classes + whitespace tole" (module: plugins/flow-next/references/html-artifacts.md)
  lavish-interactive-only-gate-must-check-2026-06-12 — "Lavish interactive-only gate must check MODE var AND env markers in-snippet" (module: plugins/flow-next/skills/flow-next-capture/references/html-lens.md)
  optional-side-effect-snippets-need-2026-06-12 — "Optional side-effect snippets need guarded git steps; check-ignore the exact fil" (module: plugins/flow-next/skills/flow-next-make-pr/html-lens.md)
  policy-claim-inversion-sweep-all-2026-06-18 — "Policy-claim inversion: sweep ALL surfaces (both ceremony copies, docs, CLI head" (module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  status-policy-map-needs-a-matching-2026-06-18 — "Status-policy map needs a matching reconcile-loop branch per rung (map ≠ write)" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md)
  backlog-select-must-not-drop-a-dep-2026-06-27 — "Backlog SELECT must not drop a dep-blocked item to NO_WORK — it routes to BLOCKE" (module: plugins/flow-next/skills/flow-next-pilot/references/backlog-mode.md)
  r2-ask-block-mis-injected-into-negation-2026-06-27 — "R2 ask-block mis-injected into negation-only autonomy prose on mirror regen" (module: scripts/sync-codex.sh, plugins/flow-next/skills/flow-next-pilot, plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  verdict-tasks-must-rewrite-not-banner-a-2026-07-03 — "Verdict tasks must rewrite, not banner, a sibling task's flipped scope" (module: .flow/tasks)
  eval-ledger-feature-rows-must-disclaim-2026-07-18 — "Eval-ledger feature rows must disclaim the optimization ratchet + reconcile deno" (module: optimization/interview)
  unit-rename-substitution-broke-trigger-2026-07-18 — "Unit-rename substitution broke trigger thresholds (turns->rounds, fn-100)" (module: plugins/flow-next/skills/flow-next-interview/references/doc-aware.md)
  grep-c-prints-0-and-exits-1-echo-0-2026-07-24 — "grep -c prints 0 AND exits 1: || echo 0 yields a two-line count" (module: plugins/flow-next/skills/flow-next-audit/workflow.md)
  changelog-entry-landed-in-a-released-2026-08-01 — "Changelog entry landed in a released section, not Unreleased" (module: CHANGELOG.md)
  codex-home-rewrite-both-spellings-2026-08-02 — "CODEX_HOME rewrite: both spellings, actionable prose, quoting, sorted-hash idemp" (module: scripts/sync-codex.sh)
  concurrent-gating-draws-soft-terms-2026-08-21 — "Concurrent gating draws + soft terms falsify a 'frozen' eval pre-registration" (module: agent-evals/studies/rolling-frontier-2026-08)
  concurrent-loop-skill-prose-linear-2026-08-22 — "Concurrent-loop skill prose: linear checklist + non-blocking claims contradict" (module: plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md)
  canonical-3c-edits-vanish-from-codex-2026-08-28 — "Canonical 3c edits vanish from Codex mirror via stale SECTION3C heredoc" (module: scripts/sync-codex.sh)
  prose-tick-lock-claim-before-read-2026-08-28 — "Prose tick lock: claim before read, serialized reap, liveness refresh, persisted" (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  delegating-cli-wrapper-inherits-2026-08-30 — "Delegating CLI wrapper inherits delegate guards, prints, truncation, races" (module: plugins/flow-next/scripts/flowctl.py)
  skill-flag-gating-a-durable-write-needs-2026-08-31 — "Skill flag gating a durable write needs exact-token parse, not substring" (module: plugins/flow-next/skills/flow-next-capture/SKILL.md)
  implementer-brief-widened-never-list-2026-09-14 — "Implementer brief widened never-list past the spec; child lost its fan-out" (module: plugins/flow-next/templates/usage.md)

bug/data/
  migrationrollback-cli-10-review-cycle-2026-05-08 — "Migration/rollback CLI: 10 review-cycle pitfalls (fn-43.3)" (module: plugins/flow-next/scripts/flowctl.py)
  paired-snapshot-setter-must-write-both-2026-06-03 — "Paired-snapshot setter must write both halves atomically (merge base)" (module: plugins/flow-next/scripts/flowctl.py)
  fence-preserving-writer-needs-fence-2026-07-02 — "Fence-preserving writer needs fence-aware readers/validators (write/read parity)" (module: plugins/flow-next/scripts/flowctl.py)
  yaml-frontmatter-writer-unescaped-2026-07-24 — "YAML frontmatter writer: unescaped newlines lose the entry; frontmatter-only wri" (module: plugins/flow-next/scripts/flowctl.py)
  adding-a-key-to-a-content-hash-orphans-2026-08-01 — "Adding a key to a content hash orphans records the old binary wrote" (module: plugins/flow-next/scripts/flowctl.py)
  docs-for-a-hash-identity-fix-inherit-2026-08-01 — "Docs for a hash-identity fix inherit the hash's precision" (module: plugins/flow-next/docs/flowctl.md)
  relaxing-a-validator-must-only-admit-2026-09-26 — "Relaxing a validator must only admit values the writer round-trips" (module: plugins/flow-next/scripts/flowctl.py)

bug/integration/
  drop-receipt-to-break-codex-2026-05-09 — "Drop receipt to break codex confabulation in long review fix loops" (module: plugins/flow-next/scripts/flowctl.py)
  set-tracker-id-rejected-github-n-2026-06-03 — "set-tracker-id rejected GitHub #N identifiers (Linear-only handle validator)" (module: plugins/flow-next/scripts/flowctl.py)
  trackers-auto-linkify-issue-key-2026-06-03 — "Trackers auto-linkify issue-key substrings inside markers (even in HTML comments" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md)
  heredoc-built-json-breaks-on-free-form-2026-06-05 — "Heredoc-built JSON breaks on free-form interpolated values" (module: skills/flow-next-qa/workflow.md)
  rp-builder-file-slices-cause-false-2026-06-10 — "RP builder file slices cause false-positive 'missing docs' review findings" (module: plugins/flow-next/skills/flow-next-impl-review)
  gh-api-f-stringifies-numeric-body-2026-06-17 — "gh api -f stringifies numeric body fields (issue_id) → GitHub 422; use -F" (module: plugins/flow-next/scripts/flowctl_tracker/)
  markerstruct-field-semantics-must-2026-06-27 — "Marker/struct-field semantics must update the PRODUCER adapter contract, not jus" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md)
  ceremony-validation-must-read-persisted-2026-06-28 — "Ceremony validation must read PERSISTED config, not re-race env; don't collapse " (module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  adding-a-review-backend-sweep-all-2026-06-29 — "Adding a review backend: sweep ALL enumeration sites (config table, stage list, " (module: plugins/flow-next/docs, plugins/flow-next/scripts/flowctl.py)
  byte-for-byte-spec-contract-branch-2026-07-01 — "Byte-for-byte spec contract: branch prose into variants, don't annotate shared l" (module: plugins/flow-next/skills/flow-next-plan-review/SKILL.md)
  skill-bash-blocks-re-declare-every-2026-07-02 — "Skill bash blocks: re-declare EVERY literal path per block (vars die across tool" (module: plugins/flow-next/skills)
  spec-named-config-keys-must-be-checked-2026-07-15 — "Spec-named config keys must be checked against shipped surface; cross-family is" (module: plugins/flow-next/skills/flow-next-setup/workflow.md)
  claude-p-clean-room-on-oauth-logins-2026-07-16 — "claude -p clean-room on OAuth logins: --setting-sources project,local; --bare an" (module: agent_docs/guidance-eval/runner.sh)
  path-handoff-template-id-slots-must-use-2026-07-19 — "Path-handoff template id slots must use canonical ids, not aliases" (module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md)
  summary-sinks-for-repeatable-mixed-2026-07-19 — "Summary sinks for repeatable mixed-outcome events need per-event lines, not one " (module: plugins/flow-next/skills/flow-next-work/phases.md)
  skill-fence-consolidation-6-contract-2026-07-20 — "Skill-fence consolidation: 6 contract regressions (var-atomicity, symlink, dry-r" (module: plugins/flow-next/skills)
  caller-facade-guards-must-cover-retro-2026-07-29 — "Caller facade guards must cover retro-fire paths" (module: plugins/flow-next/skills/flow-next-capture/workflow.md)
  caller-fakes-must-enforce-lifecycle-2026-07-29 — "Caller fakes must enforce lifecycle facade input contracts" (module: plugins/flow-next/tests/test_tracker_caller_execution.py)
  caller-oracle-must-preserve-historical-2026-07-29 — "Caller oracle must preserve historical quirks and exact observations" (module: plugins/flow-next/tests/test_tracker_caller_oracle.py)
  tracker-ownership-rewrites-require-2026-07-29 — "Tracker ownership rewrites require adjacent fidelity sweeps" (module: plugins/flow-next/docs/tracker-sync.md)
  head-bound-html-artifacts-must-not-2026-07-30 — "Head-bound HTML artifacts must not stale their own input" (module: plugins/flow-next/skills/flow-next-make-pr/html-lens.md)
  land-evidence-field-defaulted-to-off-on-2026-08-19 — "land evidence field defaulted to 'off' on configured-but-not-due paths" (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  installer-must-own-what-it-deletes-2026-08-21 — "(no title)" (module: scripts/install-codex.sh, scripts/sync-codex.sh)
  scheduler-prose-asserted-wrong-config-2026-08-22 — "Scheduler prose asserted wrong config default; slot-hold drain rules deadlock" (module: plugins/flow-next/skills/flow-next-work-rolling/references/rolling-scheduler.md)
  backend-special-case-in-a-shared-helper-2026-09-05 — "Backend special-case in a shared helper is an enumeration site too" (module: plugins/flow-next/scripts/flowctl.py)
  ci-path-classification-must-include-2026-09-05 — "CI path classification must include rename sources" (module: scripts/ci/classify_changes.py)
  cross-family-review-claims-key-on-the-2026-09-05 — "Cross-family review claims key on the writer's model family, never the host name" (module: plugins/flow-next/docs)
  headless-review-backend-error-envelope-2026-09-05 — "Headless review backend: error-envelope text must never ride the output slot" (module: plugins/flow-next/scripts/flowctl.py)
  forwarded-license-carried-the-wrong-2026-09-14 — "Forwarded license carried the wrong holder's commit contract into the bridged ch" (module: plugins/flow-next/agents/worker.md)
  plan-review-criteria-edits-must-also-2026-09-14 — "Plan-review criteria edits must also sweep workflow-rp.md (CE summary + Classic " (module: plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md)

bug/performance/
  linear-graphql-every-nodes-connection-2026-06-03 — "Linear GraphQL: every {nodes} connection needs first: — incl. workflowStates/tea" (module: plugins/flow-next/scripts/flowctl_tracker/wire/linear.py)

bug/runtime-errors/
  who-wins-ladder-must-check-the-2026-06-03 — "Who-wins ladder must check the collision case before single-field rules" (module: plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md)
  flowctl-on-disk-per-key-counter-count-2026-06-27 — "flowctl on-disk per-key counter: count by stored key + lock + coerce sort" (module: plugins/flow-next/scripts/flowctl.py)
  bash-deadline-watchdogs-orphaned-sleep-2026-07-16 — "Bash deadline watchdogs: orphaned sleep holds pipes; group-kill via setsid, not " (module: agent_docs/guidance-eval/runner.sh)
  forced-color-git-grep-output-defeats-2026-07-19 — "Forced-color git grep output defeats regex post-filter (SGR escapes)" (module: plugins/flow-next/scripts/flowctl.py)
  glob-walk-file-loads-need-lstat-screen-2026-07-19 — "Glob-walk file loads need lstat screen + RecursionError; revalidate TTL post-sta" (module: plugins/flow-next/scripts/flowctl.py)
  empty-value-semantics-leak-null-in-2026-07-20 — "Empty-value semantics leak: {} -> null in snapshot config reads; empty file -> T" (module: plugins/flow-next/scripts/flowctl.py)
  structured-review-parsers-must-2026-07-30 — "Structured review parsers must distinguish invalid from absent" (module: plugins/flow-next/scripts/flowctl.py)
  same-owner-alias-re-registration-must-2026-08-02 — "Same-owner alias re-registration must harden a weak claim, not no-op" (module: plugins/flow-next/scripts/flowctl.py)
  one-shot-keyed-to-an-earlier-captured-2026-08-19 — "One-shot keyed to an earlier-captured SHA: re-validate after the claim, release " (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  land-chain-fences-a-failed-read-is-2026-09-13 — "Land chain fences: a failed read is never permission; write multi-layer records " (module: plugins/flow-next/skills/flow-next-land/workflow.md)
  skill-fences-that-degrade-only-without-2026-09-13 — "Skill fences that degrade only without set -e: masked failures in make-pr chain " (module: plugins/flow-next/skills/flow-next-make-pr/create-and-finalize.md)

bug/security/
  rollback-path-sanitizer-must-not-2026-06-05 — "Rollback path-sanitizer must not trim/rewrite bytes; guard git clean against emp" (module: plugins/flow-next/scripts/flowctl.py)
  shell-command-allowlist-gates-must-2026-06-05 — "Shell-command allowlist gates must tokenize argv, not substring-match" (module: plugins/flow-next/scripts/hooks/ralph-guard.py)
  managed-review-transport-must-bound-2026-09-08 — "Managed review transport must bound time and protect scoped credentials" (module: plugins/flow-next/scripts/flowctl.py)
  guard-matcher-narrowing-missed-shell-2026-09-25 — "Guard matcher narrowing missed shell control words and split redirect words" (module: plugins/flow-next/scripts/hooks/ralph-guard.py)

bug/test-failures/
  rename-smoke-rewire-variable-form-cli-2026-05-09 — "Smoke discipline: variable-form CLI, hermetic env, line-level guard scope" (module: plugins/flow-next/scripts)
  test-production-path-not-parallel-construction-2026-05-21 — "Test the production path, not a parallel construction" (module: plugins/flow-next/tests, plugins/flow-next/scripts/flowctl.py)
  test-fixtures-must-mirror-upstream-zod-2026-05-26 — "Test fixtures must mirror upstream Zod enum, not concept" (module: plugins/flow-next/tests/fixtures/clawpatch-map, plugins/flow-next/scripts/flowctl.py)
  archaeology-fn-strip-can-over-strip-a-2026-07-02 — "Archaeology fn-strip can over-strip a test-pinned canonical breadcrumb" (module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md)
  final-gate-grep-for-a-forbidden-token-2026-07-02 — "Final-gate grep for a forbidden token hits the prohibition prose that bans it" (module: plugins/flow-next/skills/flow-next-impl-review)
  test-asserted-a-public-envelope-that-2026-08-01 — "Test asserted a public envelope that never carried the field" (module: plugins/flow-next/tests/test_chart_briefing.py)
  test-runner-timeout-must-kill-a-process-2026-08-04 — "Test-runner timeout must kill a process TREE whose identity outlives the shard" (module: scripts/run_tests_parallel.py)
  two-independent-resolve-calls-faked-a-2026-08-04 — "Two independent resolve() calls faked a path escape on Windows" (module: plugins/flow-next/scripts/flowctl_tracker/lifecycle/helpers.py)
  windows-83-path-test-failures-were-2026-08-04 — "Windows '8.3 path' test failures were cp1252 fixtures + unguarded geteuid" (module: plugins/flow-next/tests/test_normalize_section_content.py)
  flag-substring-assertion-passes-when-a-2026-09-23 — "Flag substring assertion passes when a longer sibling flag is present" (module: plugins/flow-next/tests/test_spec_id_routing_prose.py)

bug/ui/
  flow-nextdev-docs-page-needs-2026-06-03 — "flow-next.dev docs page needs registering in BOTH astro sidebar + site.ts navGro" (module: src/lib/site.ts)

knowledge/best-practices/
  scb-benchmark-proof-fn-163164-2026-08-04 — "SCB benchmark proof: fn-163/164 eliminated ceremony as a cost factor"
  windows-path-shims-cannot-observe-2026-08-11 — "Windows PATH shims cannot observe subprocess spawns (CreateProcess skips PATHEXT" (module: plugins/flow-next/tests)
  failures-after-a-restart-suspect-2026-08-28 — "Failures after a restart: suspect persistent state before code" (module: .flow)

knowledge/conventions/
  unattended-detection-uses-the-full-2026-09-26 — "Unattended detection uses the full autonomy marker namespace" (module: skills)

knowledge/decisions/
  factory-droid-platform-status-2026-05-2026-05-25 — "Factory Droid platform status — 2026-05" (module: plugins/flow-next/docs/platforms.md)
  tracker-sync-is-projection-not-2026-06-01 — "Tracker sync is projection, not coordination (Linear-first)" (module: strategy)
  plan-sync-skip-gate-not-viable-2026-07-03 — "A deterministic plan-sync skip-gate is not viable — do not re-attempt" (module: plugins/flow-next/skills/flow-next-work/phases.md)
  composed-brief-deleted-path-handoff-2026-07-19 — "Composed brief deleted: path-handoff replaces it (fn-103 eval)" (module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md)
  review-stall-detection-reads-resolution-2026-08-05 — "Review stall detection reads resolution; the trend heuristics are deleted (fn-168)" (module: plugins/flow-next/scripts/flowctl.py)
  bugbot-pre-push-stage-wont-do-patch-id-2026-08-07 — "Bugbot pre-push stage: won't-do - patch-ID dedup falsified live" (module: review)
  pilot-strike-recovery-is-a-cli-verb-not-2026-08-11 — "Pilot strike recovery is a CLI verb, not board-native transition detection" (module: plugins/flow-next/skills/flow-next-pilot)
  ralph-guard-reverts-its-delegation-2026-08-14 — "Ralph guard reverts its delegation amendment; bridge safety is prose-only" (module: plugins/flow-next/scripts/hooks/ralph-guard.py)
  tracked-vs-runtime-durability-contract-2026-08-14 — "Tracked-vs-runtime durability contract - done crosses it, validate respects it" (module: plugins/flow-next/scripts/flowctl.py)

knowledge/workflow/
  audit-sync-codexsh-during-planning-for-2026-04-30 — "Audit sync-codex.sh during planning for Codex mirror impact" (module: planning)
  final-integration-tasks-need-wider-impl-2026-05-26 — "Final-integration tasks need wider impl-review base" (module: review)
  pr-bot-review-loops-do-not-converge-2026-08-04 — "(no title)" (module: review-subsystem)
  split-pr-at-second-adjacent-surface-finding-2026-08-21 — "(no title)" (module: review)
  stacked-pr-squash-close-recovery-2026-08-27 — "Squash-merging a stacked PR's base permanently closes the stacked PR - rebase + successor PR is the recovery" (module: land)
  harness-capability-claims-verify-at-the-2026-08-28 — "Harness capability claims: verify at the installer, not the generator" (module: platforms)
  github-rulesets-need-an-admin-bypass-or-2026-09-11 — "GitHub rulesets need an admin bypass or spec-only commits stall" (module: ci)

===== [11/11] dependencies: ids, titles, statuses, done summaries =====
- fn-64-tracker-sync-project-flow-spec.2 [todo] - Adapter interface contract: setIssueRelation / listIssueRelations + relation struct
    Documented the normalized dependency-relation contract in adapter-interface.md: added `setIssueRelation(issue, blockedBy)` / `listIssueRelations(issue)` to the transport table, a new `relation` struct `{from, to, type, source}`, the once-stated blocked-by direction convention, and the mandatory read-before-write idempotency + never-delete-non-ours provenance rules — cross-linked to fn-64.1's depRelations ledger and the fn-64.4 fenced-block/body-merge exclusion. Contract-only doc that unblocks fn-64.3 and fn-64.4.

