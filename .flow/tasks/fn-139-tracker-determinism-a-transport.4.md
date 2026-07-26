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
- [ ] Scoped resolution (`--scope destination`, `--scope capabilities`) tested for both

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
