---
satisfies: [R2, R5, R12]
---
# fn-130-reached-path-skill-prompt-optimization.4 Route Tracker Sync common and selected adapters

## Description
Replace Tracker Sync all-adapter eager loading with common reconciliation instructions plus exactly the selected provider adapter and only the needed Linear transport fallback. Prove behavior against fake production-shaped transports; never touch live trackers.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md`, `steps.md`, `references/*.md`, tracker tests/fixtures for state, backlog, receipts, mirror, GitLab, Jira and new routing traces, corresponding Codex mirror, `optimization/reached-path/tracker-*`.

### Approach
- Classify common identity/body/status/comments/dependency/reconciliation rules separately from provider transport instructions.
- Load Linear ladder first, then MCP or GraphQL only when selected/reached; load one of GitHub/GitLab/Jira for other providers.
- Preserve create-if-unlinked, push/pull/reconcile direction, semantic three-way body merge, who-wins IDs, conflict/defer receipts, backlog mode, and status/comment/dependency projection.
- Use recorded normalized payloads and fake transports through production command/wire forms; auth/tool absence must degrade exactly as baseline.
- Sweep the whole tracker tree and docs for per-adapter authority; a slash-list grep is not sufficient.

### Frozen fixtures
- inactive/no config; malformed/unknown provider; linked and unlinked specs.
- Linear MCP success, MCP unavailable, GraphQL fallback success, no transport.
- GitHub gh, GitLab glab/REST, Jira Cloud/DC.
- push, pull, reconcile; body conflict/no conflict; status collision; comments; dependency blocks; backlog relation states; auth failure/no-op.

### Investigation targets
**Required**
- `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md:14-17` — current eager-read contract.
- `plugins/flow-next/skills/flow-next-tracker-sync/steps.md` — shared operation flow.
- `plugins/flow-next/skills/flow-next-tracker-sync/references/adapter-interface.md` — common provider boundary.
- `plugins/flow-next/tests/test_tracker_sync_state.py` — reconciliation state fixtures.
- `plugins/flow-next/tests/test_tracker_sync_{gitlab,jira,mirror_parity}.py` — adapter/mirror assertions.

**Optional**
- `.flow/memory/knowledge/decisions/tracker-sync-is-projection-not-2026-06-01.md` — projection-not-coordination lock.
- fn-85 Tracker frozen grammar and fn-122 whole-tree lessons.

## Acceptance
- [ ] Task input prompt hashes match version-adjusted `V1/B1`; every structural candidate compares against `B1`, never original `B0`.
- [ ] Baseline and candidate route traces cover inactive, malformed, every provider, Linear fallback, operation direction, and conflict/defer states.
- [ ] Each configured path loads common refs plus only its selected adapter/transport; inactive loads no adapter; unknown state fails safe.
- [ ] Fake transports use production command/payload forms and make zero live external writes.
- [ ] Create/link, body/status/comments/dependency reconciliation, who-wins rules, receipts, defers, backlog and auth/no-op behavior match baseline.
- [ ] Existing tracker suites plus new routing assertions pass on canonical and Codex mirror.
- [ ] Measured selected-path reduction is recorded per provider; any adapter whose zero-loss matrix fails is reverted and logged independently.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
