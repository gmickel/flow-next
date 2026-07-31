---
satisfies: [R16, R42, R54, R55]
---
# fn-135-chart-decision-map-discovery-for.5 Project charts through the deterministic tracker facade

## Description
### Objective

Add optional full-lifecycle chart projection and safe tracker-locator re-entry through the post-fn-141 deterministic tracker lifecycle facade. `.flow/` remains canonical; remote parent/child state, type/attendance, blocking, safe evidence, compact parent rollups, and locators are idempotent projections with explicit capability degradation and reconcile recovery.

### Dependency gate

Re-anchor on fn-141 before starting. Its lifecycle facade, authoritative caller matrix, and tracker-runner teardown must be present. Do not implement against the deleted/legacy runner or copy adapter command prose into chart.

Task 3 is a direct dependency: the projected transition matrix includes briefing/done, reopen, and stale-link events that task 3 implements. This task may run in parallel with task 6 (disjoint files).

### Exact files

- `plugins/flow-next/scripts/flowctl.py` and the post-fn-141 `plugins/flow-next/scripts/flowctl_tracker/` modules that own locator, hierarchy, relation, capability, ledger, and lifecycle sync — extend the facade, not a chart-only transport stack.
- `plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md` — define chart parent/child locator plus blocking projection and lossless/degraded capabilities.
- `plugins/flow-next/skills/flow-next-chart/SKILL.md` or `workflow.md` — add only the bridge-active/per-event gate and one facade call/recovery handoff required by fn-141.
- `plugins/flow-next/tests/test_chart_tracker_projection.py` — new local-only, typed locator/URL re-entry, lifecycle/rollup matrix, four-adapter contract, partial-success/reordered reconcile, dedup, and degradation suite.
- fn-141's authoritative caller-inventory test/file — add chart as a lifecycle caller using its existing matrix format.

### Investigation targets

- Reuse the relation/provenance ledger around `flowctl.py:23533-23681` and fn-140/141 result envelopes. Add chart-specific locator state without mutating spec metadata or making tracker ids chart identity.
- Generalize the typed subject/locator boundary around `flowctl.py:31749-31889`; do not bolt a chart-only transport onto the spec-id facade. Reuse atomic identity completion/recovery at `plugins/flow-next/scripts/flowctl_tracker/lifecycle/linkstate.py:70-149`, event/evidence marker dedup and aggregate receipts at `flowctl_tracker/facade/helpers.py:280-399`, and the normalized locator/capability/result contracts in `skills/flow-next-tracker-sync/references/adapter-interface.md:6-121`.
- Extend identifier resolution around `flowctl.py:8132-8157` with `flowctl chart locate`, but keep strict display-ID validation separate from selector resolution. Reuse the `{id,identifier,url}` plus retry-key recovery shape around `flowctl.py:24380-24439`. Canonicalize before every read/write/receipt path; never weaken durable-id stale-parent guards.
- Parent hierarchy: chart parent plus decision children where the provider supports it; otherwise labelled/linked flat issues with an explicit degraded capability in the result.
- `blocked_by` projects to native blocking only when supported. `depends_on` does not masquerade as the same relation.
- Project decision `type`, `attendance`, local status, safe gist/evidence links, and chart-qualified identity through native fields/labels where lossless, otherwise through an owned body block with explicit degradation. Never copy full answer bodies, unsafe assets, credentials, or acceptance-criterion source tags.
- Define the transition matrix explicitly: create/wire; claim/release; resolve; supersede; out-of-scope; briefing/done; abandon; reopen/stale-link. Each committed local revision produces one idempotent event marker and aggregate receipt. Claim/release may refresh the owned block/counts but never masquerades as provider workflow status.
- Parent rollup is compact projection only: chart Outcome/status; counts for actionable, blocked, claimed, resolved, superseded, out-of-scope, and parked; latest resolved D-ID/title/safe gist; current frontier. Native parent/child status changes use existing normalized mappings only when lossless/configured; otherwise the body/label carries local status and the result reports degradation.
- Remote create may succeed before relation or local ledger write. Record enough resolved identity/provenance to make the next reconcile converge without duplicate issues/comments/edges.
- Local transition always commits first. Partial, failed, reordered, or unsupported remote operations persist completed steps/receipt/revision so retry or reconcile converges without rolling back chart state or publishing a stale parent rollup.
- URL lookup is strictly local against stored normalized locators. Accept only configured supported provider URL forms; normalize scheme/host case and provider-approved cosmetic suffixes, reject credentials, redirects, wrong host/project, ambiguity, unrecorded URLs, and stale/conflicting durable ids. Never search the network or match titles.
- Parent URL returns the chart. Open decision URL returns that D-ID. Resolved/superseded decision URL returns history plus replacement/frontier metadata without selecting different work. Failures use the existing v1 error classes with specific codes such as `unresolved_locator`, `stale_id`, or `unsupported_capability`, and mutate nothing.
- With `tracker.charts` off, bridge inactive, no tracker configured, or unsupported capability, local chart mutation succeeds and the result says exactly what was skipped/degraded.

### Required behavior and examples

- Creating a projected chart records parent and child locators once. Retrying after parent or child remote success but before local ledger publication completes the same identity through the retry key.
- Resolving D4 updates the child with local status, safe gist, and approved evidence references, then refreshes the parent counts/latest-resolution/frontier block. A failure between those steps records the completed child update and converges the parent on reconcile without duplicate comments.
- Superseding D3 with D9 keeps both children addressable, marks the former status/gist without deleting it, refreshes affected blocking relations, and rolls up the new current frontier.
- Pasting a stored decision URL resolves to the canonical chart-qualified D-ID, title, and local record link without a remote call. An unknown or wrong-project URL fails before any chart/tracker write.
- Flat or field-limited providers retain linked parent/child identity and owned body blocks, return exact degraded capabilities, and never flatten `depends_on` into `blocked_by`.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_tracker_projection test_tracker_sync_mirror_parity -q
```

Use the exact fn-141 caller-matrix test name once that task lands; do not invent a parallel matrix.

### Non-goals

- No new adapter or tracker-canonical chart state.
- No MCP/CLI transport ladder reintroduced into chart prose.

## Acceptance
- Task starts only after fn-141 lifecycle facade/caller matrix is present and chart uses that single facade path.
- `.flow/` remains authoritative; projection stores provider locators and provenance in an idempotent local ledger.
- All four adapters cover native or explicitly degraded parent/child, decision type/attendance/status, blocking, safe evidence, and compact parent-rollup behavior; `depends_on` is never projected as an indistinguishable blocking edge.
- Create/wire, claim/release, resolve, supersede, out-of-scope, briefing/done, abandon, and reopen/stale-link transitions are local-first, revisioned, event-deduplicated, receipt-backed, and covered by the lifecycle matrix.
- Remote partial/reordered success followed by retry/reconcile converges child state and the current parent rollup without duplicate parents, children, relations, comments, evidence markers, or status transitions.
- `flowctl chart locate` resolves canonical chart/D-ID, stored identifier, and safe stored URL selectors only through the local ledger. Unknown, ambiguous, credential-bearing, wrong-host/project, stale-parent, and conflicting selectors return structured failures with zero mutation and no network/title lookup.
- Parent/open-decision URLs read back canonical identity; resolved/superseded decision URLs remain historical and never silently select replacement work.
- Disabled/inactive/unconfigured/unsupported tracker states never block local chart operations and have stable structured results.
- Chart is added to fn-141's authoritative caller inventory and focused tracker commands pass.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
