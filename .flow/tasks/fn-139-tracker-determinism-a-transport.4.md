---
satisfies: [R9,R11]
---

# fn-139-tracker-determinism-a-transport.4 Per-adapter resolution + capability truth table + Linear tiebreak
# fn-139-tracker-sync-determinism-flowctl-owns.4 Capabilities: attachments, relations, tier detection, degradation

## Description
Resolve `destination` + `capabilities` for all four adapters.

**Jira pins status ids, NOT transition ids.** `jira.md:738` states transition ids are valid only from the current status, verified live (To Do -> In Progress -> Done each surfaced different ids). A status write must still GET transitions per issue; the cache buys correctness, not latency.

GitLab pins the **numeric** projectId (the path changes on rename) plus `plan` for tier detection - trials are GROUP-scoped, so a personal-namespace project stays Free.

Implement the capability truth table from the spec exactly; `subIssues` and `deleteIssue` are kept with consumers assigned in B. A failed TTL re-probe reports via the separate `probe` field, not `degraded`.

`resolve --select` persists the Linear tiebreak (`type: started` maps to two states), validated against live candidates.

## Acceptance
- [ ] All four adapters resolve every field in the Architecture table
- [ ] Jira caches STATUS ids only; no transition id is persisted
- [ ] GitLab numeric projectId + plan; group-scoped trial vs personal namespace distinguished
- [ ] Capability truth table matches the spec exactly for all four
- [ ] Failed re-probe reports via `probe`, never `degraded`
- [ ] `resolve --select` validates against live candidates before persisting

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
