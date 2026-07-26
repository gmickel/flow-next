---
satisfies: [R9, R11, R15]
---

# fn-139-tracker-determinism-a-transport.4 Per-adapter destination + capability resolution, incl. Linear tiebreak
# fn-139-tracker-sync-determinism-flowctl-owns.4 Capabilities: attachments, relations, tier detection, degradation

## Description
Resolve `destination` + `capabilities` for all four adapters per the Architecture table: GitHub owner/repo; GitLab numeric projectId + path + host + `plan` (the path changes on rename, so the id is what gets pinned); Linear teamId + stateIds + labelIds; Jira baseUrl + projectKey + projectId + issueTypeId + apiVersion 2 + style + transitions.

GitLab tier detection via `GET /namespaces/:id -> plan`. Verified both ways during smoke: Free rejects `is_blocked_by`, Ultimate accepts it, and trials are GROUP-scoped so a personal-namespace project stays Free.

`resolve --select` persists the human's Linear tiebreak (`type: started` maps to two states), validated against live candidates.

Finally assert the bridge-inactive path is byte-for-byte unchanged.

## Acceptance
- [ ] All four adapters resolve every field in the Architecture table
- [ ] GitLab `plan` detected; group-scoped trial vs personal namespace distinguished
- [ ] `resolve --select` validates against live candidates before persisting
- [ ] `resolvedAt` stamped only when all required fields are present
- [ ] Bridge-inactive path byte-for-byte unchanged (reached-path harness)
- [ ] Capabilities correct per adapter (GitHub attachments:false, deleteIssue:false)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
