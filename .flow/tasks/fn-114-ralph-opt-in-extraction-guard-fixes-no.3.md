# fn-114-ralph-opt-in-extraction-guard-fixes-no.3 Guard defect fixes (structured done-signal, dual-platform, gated debug)

## Description
Guard defect fixes (the guard still ships, opt-in).

**Size:** M
**Files:** plugins/flow-next/skills/flow-next-ralph-init/templates/ralph-guard.py (or its current home), templates/ralph.sh, tests

### Approach

- Read spec section C. Six fixes:
  7. done-detection: replace the done/updated/completed word sniff (locate by content, audit refs ralph-guard.py:733-740) with a structured signal (tool_response exit code, or require --json and parse it).
  8. Platform matchers PLAN DECISION (in spec): ralph-init writes host-appropriate matchers per platform AND the guard body accepts ("Bash","Execute") for shell and ("Edit","Write","Create","ApplyPatch") for file tools.
  9. Write-tool receipt bypass: extend Edit|Write handling to block receipt-path writes pre-review (parity with Bash patterns) - prefer this over deleting the Bash-side ordering; keep the Stop-hook as final enforcement.
  10. Debug log: gate the unconditional /tmp append behind RALPH_GUARD_DEBUG=1; use tempfile.gettempdir() (Windows parity).
  11. Dead weight: delete RALPH_GUARD_VERSION no-op constant; ralph_e2e_test.sh - WIRE it into agent_docs/local-dev.md (one sentence pointing at it) rather than deleting (cheaper, keeps the harness); the rp pick-window state-file write is already gone (fn-111) - verify, note.
  12. find_active_runs: parse progress.txt via key=value contract lines (extend ralph.sh's promise=COMPLETE pattern) - lands in ralphctl.py per task 2's move.
- Guard tests (test_ralph_guard*) re-pinned to the new signals; keep the fn-55 delegation-shape assertions intact.
- NO git commands, no em dashes; focused suites only.

### Acceptance

- [ ] All six fixes in; done-detection structured; matchers dual-platform; debug log gated + tempdir; key=value progress contract
- [ ] test_ralph_guard* suites green re-pinned; fn-55 canonical-delegation assertions unchanged
- [ ] local-dev.md points at ralph_e2e_test.sh

## Acceptance
- [ ] TBD

## Done summary
All six guard fixes shipped: (1) done-detection is structured - exit code, --json status, or the exact completion line; the done/updated/completed word sniff is gone, fail-closed by design when hosts omit all three signals. (2) Dual-platform per the plan decision: guard body accepts Bash|Execute and Edit|Write|Create|ApplyPatch; ralph-init registers host-appropriate matchers. (3) File-tool receipt-path writes blocked pre-review (Bash parity), PostToolUse resets after receipt write. (4) Debug log gated behind RALPH_GUARD_DEBUG=1, tempfile.gettempdir() for Windows parity. (5) RALPH_GUARD_VERSION deleted; ralph_e2e_test.sh wired into local-dev.md; fn-111's pick-window removal verified. (6) key=value progress contract: parse_progress_kv in ralphctl, ralph.sh writes one key per line, flowctl soft-probe parses the same contract (deliberate no-import duplication per .2 design). fn-55 canonical-delegation assertions unchanged. Host review: synced the drifted dual-copy (delegate edited canonical flowctl only). Guard suites 96 green; full parallel suite 88 files / 1883 tests / 0 failures / 71.3s; sync-codex x2.
## Evidence
- Commits: 5d9d9fe3e64502e30d1bed4e0e2367296424c0a7
- Tests: python3 scripts/run_tests_parallel.py (88 files, 1883 tests, 0 failures, 71.3s), test_ralph_guard* + test_ralphctl 96 green, fn-55 delegation assertions unchanged
- PRs: