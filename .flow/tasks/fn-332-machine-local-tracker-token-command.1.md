---
satisfies: [R1, R2, R3, R4]
---
# fn-332-machine-local-tracker-token-command.1 Implement machine-local tracker token command

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Machine-local tracker token command (MergeFoundry ask, approved by Gordon 2026-11-18):

- `FLOW_TRACKER_TOKEN_COMMAND_LINEAR` / `_JIRA` hold a JSON argv read before the tracked `tracker.perTracker.tokenCommand`; the token variable still wins. A failed machine-local command stops there (no fallback). A malformed value fails as `auth` naming the variable without echoing it; a missing machine-local executable names the variable, never its path. Setting it for Linear skips the MCP create route unless an explicit transport preference says mcp (same as the tracked key).
- Docs: runtime tracker-sync doc, schema description, tracker-sync skill (with the order) and its conduct checklist; CHANGELOG Unreleased entry.
- User-shaped run through `flowctl tracker resolve`: malformed value, failing command and a working command (Linear 401 for a fake key) all behaved as specified; the tracked command never ran.

Declined #3: an explicit preferredTransport/transport of mcp keeps the MCP route; the tracked tokenCommand behaves the same, and the re-review agreed.

stage: impl-review - ran (NEEDS_WORK: skill omitted the order, missing executable leaked its path; fixed; re-review SHIP) (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: ec7f9ca82a30ff51c7b5dfa5aa86e8eed18db996, 52380fe767838199dac1623502f492d50c4d817c, 2e2a1cfde51a828cdf00d03eed69ebb8b7e08fe6, 0e071682f5f618e666f70b5e3c71a3e79ed4229b, 7ba1997156f0455e2244d253c6eff5c0330ffdcc
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: