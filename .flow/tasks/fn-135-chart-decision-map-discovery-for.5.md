---
satisfies: [R16, R42]
---
# fn-135-chart-decision-map-discovery-for.5 Project charts through the deterministic tracker facade

## Description
### Objective

Add optional chart projection through the post-fn-141 deterministic tracker lifecycle facade. `.flow/` remains canonical; remote parent/child, blocking, and provenance are idempotent projections with explicit capability degradation and reconcile recovery.

### Dependency gate

Re-anchor on fn-141 before starting. Its lifecycle facade, authoritative caller matrix, and tracker-runner teardown must be present. Do not implement against the deleted/legacy runner or copy adapter command prose into chart.

### Exact files

- `plugins/flow-next/scripts/flowctl.py` and the post-fn-141 `plugins/flow-next/scripts/flowctl_tracker/` modules that own locator, hierarchy, relation, capability, ledger, and lifecycle sync — extend the facade, not a chart-only transport stack.
- `plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md` — define chart parent/child locator plus blocking projection and lossless/degraded capabilities.
- `plugins/flow-next/skills/flow-next-chart/SKILL.md` or `workflow.md` — add only the bridge-active/per-event gate and one facade call/recovery handoff required by fn-141.
- `plugins/flow-next/tests/test_chart_tracker_projection.py` — new local-only, four-adapter contract, partial-success reconcile, dedup, and degradation suite.
- fn-141's authoritative caller-inventory test/file — add chart as a lifecycle caller using its existing matrix format.

### Investigation targets

- Reuse the relation/provenance ledger around `flowctl.py:23533-23681` and fn-140/141 result envelopes. Add chart-specific locator state without mutating spec metadata or making tracker ids chart identity.
- Parent hierarchy: chart parent plus decision children where the provider supports it; otherwise labelled/linked flat issues with an explicit degraded capability in the result.
- `blocked_by` projects to native blocking only when supported. `depends_on` does not masquerade as the same relation.
- Remote create may succeed before relation or local ledger write. Record enough resolved identity/provenance to make the next reconcile converge without duplicate issues/comments/edges.
- With `tracker.charts` off, bridge inactive, no tracker configured, or unsupported capability, local chart mutation succeeds and the result says exactly what was skipped/degraded.

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
- All four adapters cover native or explicitly degraded parent/child and blocking behavior; `depends_on` is never projected as an indistinguishable blocking edge.
- Remote partial success followed by retry/reconcile converges without duplicate parents, children, relations, or comments.
- Disabled/inactive/unconfigured/unsupported tracker states never block local chart operations and have stable structured results.
- Chart is added to fn-141's authoritative caller inventory and focused tracker commands pass.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
