# fn-64-tracker-sync-project-flow-spec.5 projectDepRelations transport-blind skill hook (steps.md/SKILL.md): push+reconcile, warnings, completed-blocker, never-clobber, receipts

## Description
### Goal
Wire the transport-blind `projectDepRelations` hook into the skill spine so dependency projection actually runs on push/reconcile — resolving edges, calling the adapters, dedup, warnings, completed-blocker handling, never-clobber, and event-tagged receipts. **Satisfies R3, R4, R5, R6, R8.**

### Investigation targets
- `skills/flow-next-tracker-sync/steps.md:131-153` (push/comment skeleton) + `:163-180` (reconcile). Attach a new `projectDepRelations(spec, issue)` hook on BOTH push and reconcile paths, alongside `projectReadiness` (`:146,166`) — that one-way pull projection is the closest existing model (change-only receipt, never advances `lastSyncedAt`).
- The hook flow: `flowctl sync list-dep-relations` (fn-64.1) → for each resolved pair call `setIssueRelation` (fn-64.3/.4) after `listIssueRelations` read-before-write → record provenance via `flowctl sync set-dep-relation`.
- Warnings: dep spec with no tracker link → warning naming the dep spec id, sync continues (item-level isolation). Surface on the `sync receipt` using the fn-57 `operation: <verb> <id>, event: <key>` grammar verbatim (memory: mirror-regen-exposes-latent-canonical).
- Completed-blocker: dep issue Done/Closed → keep the relation, do NOT feed `ready=true` gating; must not regress fn-58 readiness.
- Never-clobber + who-wins: only remove relations in our `depRelations` ledger; evaluate the collision case (flow added / tracker removed concurrently) BEFORE per-side rules (memory: who-wins-ladder-must-check-collision-first); default to surface/defer.
- Transport unreachable → `noop` receipt; surfaced conflict → `sync defer` + `queued` receipt; genuine transport failure → `errored`. Never use a "deferred" status (not in the enum); never block the lifecycle.
- SKILL.md: extend the "flowctl owns / skill owns" table and the Forbidden list for the new hook.
## Acceptance
- [ ] `projectDepRelations` runs on push + reconcile (modelled on `projectReadiness`); idempotent across reruns (R3).
- [ ] Missing-link warning surfaced + receipted with fn-57 `operation … event …` grammar (R4); sync continues (item-level isolation).
- [ ] Completed-blocker (local dep `done`): relation kept, NOT fed into `ready=true` gating; must not regress fn-58 (R5).
- [ ] Never-clobber: only relations in the `depRelations` ledger are eligible for removal; manual relations untouched (R6).
- [ ] Collision rule: an edge in `depRelations` AND still in `depends_on_epics` but MISSING remotely → evaluate the collision case BEFORE per-side rules; emit `sync defer` + a `queued` receipt; do NOT silently recreate. Explicit test/coverage.
- [ ] Self-edge skipped with a warning; cycles projected as independent direct edges only (no traversal).
- [ ] GitHub fenced-block exclusion (canonical `tracker-body-for-merge`): strip the `<!-- flow:deps -->` region BEFORE `baseHashTracker`, `mergeBaseTracker`, and fetched tracker-body comparisons; preserve/reinject only on the GitHub issue write. Reconcile never folds flow’s own block back into the spec / render never overwrites it (R10).
- [ ] Skill stays transport-blind — no Linear-vs-GitHub branching (R8). Transport-unreachable → `noop` receipt, never blocks.
- [ ] A dry-run round-trip against a linked spec + linked dep produces the expected blocked-by edge (Linear) and native-dep/fenced-block (GitHub) with no duplicates on rerun.
## Done summary
Wired the transport-blind projectDepRelations hook into the tracker-sync skill spine (steps.md push + reconcile, modelled on projectReadiness): depends_on_epics edge enumeration via flowctl sync list-dep-relations, missing-link warnings in fn-57 grammar, read-before-write project + ledger provenance, completed-blocker keep-not-regate, strictly-additive never-clobber with collision-before-per-side-rules deferring to queued, self-edge/cycle no-traversal handling, and the body-merge.md Step 0.5 tracker-body-for-merge transform that strips the flow-owned <!-- flow:deps --> block at the hash boundary (R10). Extended SKILL.md owns-table + boundaries.
## Evidence
- Commits: a5b5e0319ba979a2600c0ced19f025e50391051d
- Tests: python3 -m unittest plugins.flow-next.tests.test_tracker_sync_state (30 passed)
- PRs: