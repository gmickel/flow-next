---
satisfies: [R1, R2, R3]
---
# fn-324-unready-a-tracker-issue-and-link-named.1 Implement Unready a tracker issue and link named issues in any id mode

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Added `flowctl tracker wire unready`: reads the issue, decides readiness with the readyState projection's match, then moves Linear/Jira to the resolved backlog state through the existing status writer, or drops the ready label on GitHub/GitLab, and reads back. Typed errors: ready_state (no call), backlog_slot and transition_unreachable (no write), readback. Capture now links a named issue in flow-id mode (sync set-tracker-id), seeds both merge-base halves from the issue body, and skips the capture push and retro-fire when the read or link fails. Docs, adapter table and Codex mirror updated; tracker MANIFEST regenerated.

Live recordings (2026-11-15): GitHub gmickel/test#1, GitLab localhost flownext/flownext#1, Linear FLOW-106 (move, no-change, unset, no backlog slot), Jira flownext KAN-6 (move via transitions, no-change, no backlog slot). R2 live on Linear: FLOW-107 linked and pushed with no second issue; FLOW-108 (old seed) noop vs FLOW-109 (issue-body seed) pushed. All test issues closed or cancelled.

stage: impl-review - ran codex three-lens NEEDS_WORK (3 findings: first-push seed no-op, failed link falls through to create, label `from` docs) then re-review SHIP (model: gpt-6.1-sol)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: cfba2324a6b807bde54b1b91a73fb6b231c033bc, b9ec56df9a6b62c5b2eb10c6854e3e47e9df58df, f2f26c0187dc478e0430a3915c7be842a00c5c00
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_tracker_*.py' (repo root)
- PRs: