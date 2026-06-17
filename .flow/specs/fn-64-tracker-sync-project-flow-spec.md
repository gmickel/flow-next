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
