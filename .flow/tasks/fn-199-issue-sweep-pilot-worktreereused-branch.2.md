---
satisfies: [R3, R4]
---
# fn-199-issue-sweep-pilot-worktreereused-branch.2 flowctl tracker wire list-states: read-only state enumeration (Linear + Jira)

## Description
Add a context-free wire verb list-states to the flowctl_tracker wire package, registered like list-open/attach-get (no locator). Reuse existing provider fetch paths: Linear GraphQL workflowStates (id, name, type, pageInfo.hasNextPage - mirror the single-page query in facade/projections.py; providers/linear.py fetch_states may be reusable); Jira GET /rest/api/<v>/project/<key>/statuses (flatten to unique statuses; type = statusCategory key). Output shape is EXHAUSTIVE per spec API Contracts: {"states": [{"id","name","type"}], "complete": bool}; complete=false with partial states + exit 0 on truncation (Linear hasNextPage). GitHub/GitLab -> typed unsupported TrackerError (no workflow-state pool); missing/unresolved destination -> unresolved; malformed/transport -> transport. Non-JSON mode: human rendering consistent with other wire verbs. NO writes to .flow/config.json or any .flow/ file on any path.

Tests (G2, behavior only): success shape per provider, truncated -> complete:false, unsupported providers, unresolved destination, malformed response, and the no-write invariant across success/truncated/error outcomes. Update MANIFEST via python3 scripts/gen_tracker_manifest.py; refresh SOURCE_SHA256 pin if flowctl.py changes; run ./scripts/sync-codex.sh twice.

## Acceptance
R3: flowctl tracker wire list-states --json returns the exhaustive shape with a trustworthy complete signal on Linear and Jira; typed errors for github/gitlab (unsupported), unresolved destination, transport/malformed; truncation -> partial + complete:false, exit 0. R4: test-asserted no-write invariant on .flow/config.json across all outcomes. gen_tracker_manifest + sync-codex idempotent; focused tracker suites green.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
