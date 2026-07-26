---
satisfies: [R9]
---

# fn-139-tracker-determinism-a-transport.4 Per-adapter resolution + capability truth table + Linear tiebreak
# fn-139-tracker-sync-determinism-flowctl-owns.4 Capabilities: attachments, relations, tier detection, degradation

## Description
Resolve `destination` + `capabilities` for **GitHub and GitLab**, plus their scoped-resolution tests.

GitHub: `owner`, `repo`. Capabilities per the truth table - `attachments: false` (no API, 404), `subIssues: true`, `deleteIssue: false` (close `not_planned` only).

GitLab: **numeric** `projectId` (the path changes on rename), `projectPath`, `host`, **`namespaceId`**, `plan`. The tier probe is `GET /namespaces/:id`, which is why `namespaceId` is pinned - without it the TTL re-probe costs an extra lookup. Trials are **GROUP-scoped**, so a personal-namespace project stays Free even while a group of the same user is on Ultimate; `blockedBy` is plan-dependent.

A failed TTL re-probe reports via the separate `probe` field, never `degraded`.

## Acceptance
- [ ] GitHub + GitLab resolve every field in the Architecture table
- [ ] `namespaceId` pinned; TTL re-probe is one request
- [ ] Group-scoped trial vs personal namespace distinguished (both directions tested)
- [ ] Capability truth table matches exactly for both providers
- [ ] Failed re-probe reports via `probe`, never `degraded`
- [ ] GitLab is the ONLY provider with a TTL re-probe (its plan-gated `blockedBy`); GitHub's capabilities are static and never re-probed
- [ ] Scoped resolution (`--scope destination`, `--scope capabilities`) tested for both

## Done summary
GitHub + GitLab resolution shipped on the injected-executor seam.

- github: destination via gh repo view (owner, repo); capabilities are the static truth-table row (attachments false, blockedBy false, subIssues true, deleteIssue false) with NO network path (tested by passing execute=None); never TTL-reprobed.
- gitlab: destination pins numeric projectId, projectPath, host, namespaceId. Host is derived from the response web_url when unset (never a gitlab.com default). Subgroup projects pin the ROOT billing namespace via one extra resolution-time lookup so the TTL re-probe stays exactly one request (GET /namespaces/:id). Plan is EVIDENCE: absent/unknown plan fails the probe; fresh capability resolution errors (never a silent blockedBy:false) while a TTL re-probe keeps the prior value and reports via probe, never degraded. Group-scoped trials vs personal namespaces tested in both measured directions.
- providers.resolver_for dispatch; unshipped providers raise KeyError.
- Scoped --scope destination/capabilities semantics tested through resolve_transaction for both providers.

3 review rounds (codex): round 1 was a sandbox transport failure (refunded); round 2 found the host-persistence bug, the missing-plan-as-false bug, and unguarded nested JSON, all fixed with 13 regression tests; round 3 SHIP with R9 met for these providers.
## Evidence
- Commits: 306a4076, 6bc91d3b
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_resolution_github_gitlab -q, python3 scripts/run_tests_parallel.py
- PRs: