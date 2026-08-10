---
satisfies: [R7]
---
# fn-179-issue-batch-r-id-parser-straggler.4 flowctl start --reclaim: identity repair distinct from --force takeover

## Description
Spec fn-179 item 6 (#316). Add --reclaim to flowctl start: rewrites the claimant with a repair claim note (distinct wording from the --force takeover note). No identity validation, no sibling-warning heuristic. --force unchanged.

**Files:** plugins/flow-next/scripts/flowctl.py (`cmd_start`) + `.flow/bin/flowctl.py` dual copy; start/claim tests

## Acceptance
R7 of the spec. Both notes distinguishable in the record; existing --force tests green.

## Done summary
flowctl start --reclaim per fn-179 R7 (#316). Relaxes exactly two identity gates (claimed-by-another, in_progress owned by another); dependency/blocked/done gates unchanged and still --force-only. Repair note "Reclaimed from <identity> (identity repair)" distinct from --force takeover note "Taken over from <identity>"; --force path byte-for-byte unchanged; explicit --note wins but claimant still rewritten; unclaimed/self-claimed = normal claim, no repair note; no sibling-identity heuristic (declined ledger honored). No-flag error now also names --reclaim for discoverability. 10 new focused tests (test_start_reclaim.py).
## Evidence
- Commits: c43fbacc
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_start_reclaim -q (10 OK), test_portable_locks test_status_source (21 OK), test_tracker_distribution test_prompt_text_pinned (25 OK)
- PRs: