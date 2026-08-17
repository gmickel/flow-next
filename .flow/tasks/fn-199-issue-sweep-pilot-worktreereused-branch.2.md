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
Added `flowctl tracker wire list-states`: a read-only, context-free wire verb (R3) enumerating workflow states for Linear (single-page GraphQL workflowStates with first:100; hasNextPage -> partial states + complete:false, exit 0) and Jira (unpaginated project statuses flattened unique-by-id, always complete:true), returning the exhaustive shape {"states":[{"id","name","type"}],"complete":bool}. GitHub/GitLab return a typed CAPABILITY error (subtype workflow_states) before any transport call; unresolved destination -> UNRESOLVED; malformed/transport -> TRANSPORT. R4 no-write invariant is test-asserted across success/truncated/capability/malformed outcomes (config.json byte-identical + no new .flow files). Conformance matrix and verb-surface pins extended; MANIFEST regenerated; sync-codex idempotent. Implementation was bridged to cursor-grok-4.6-high per the run's explicit routing; the host verified the diff, ran gates, and committed.

baseline: green (focused tracker suites, 168 tests OK pre-edit)

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)

stage: impl-review - ran (model: claude-fable-5, host backend, rounds NEEDS_WORK/NEEDS_WORK/SHIP; fixes: surface pin, loud malformed-body on both providers, hasattr guard, _PAGE_SIZE, api-v2 parity)
## Evidence
- Commits: a8186e4641ce0530bf5110305e620ef2081822c5, 6fc6dfbf, 540d381e
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_wire test_tracker_conformance test_tracker_distribution -q (176 tests OK), python3 scripts/gen_tracker_manifest.py (45 files), ./scripts/sync-codex.sh x2 (idempotent, rc=0 both), uvx ruff@0.16.0 check plugins/flow-next/scripts (clean), implementer: cursor-agent -p --force --model cursor-grok-4.6-high (bridged; host kept git/tests/judgment), cd plugins/flow-next/tests && python3 -m unittest test_tracker_wire test_tracker_conformance test_tracker_distribution test_startup_bootstrap test_flowctl_surface -q (205 tests OK, post-fix rounds)
- PRs:stage: plan-sync - ran (task .3 docs scope updated: api-v2 pin, INVALID_INPUT taxonomy, malformed-body behavior, adapter-interface.md targets; model: claude-fable-5 subagent)
