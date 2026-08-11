---
satisfies: [R5, R6]
---
# fn-184-pilot-strikes-deterministic-clear-verb.3 Decision record, CHANGELOG, propagation + full gate

## Description
Spec fn-184 R5-R6. Decision record for the deferred board-native alternative (observed-out-of-ready-since-strike bit; tick-granularity caveat) so it is not re-proposed cold. CHANGELOG Unreleased crediting @sn-furali (#325), user-outcome-first. Dual copies, tracker manifest, sync-codex twice, full suite + pinned ruff. The #325 answer must be postable by link after merge.

## Acceptance
R5, R6 of the spec. Full gate green; no version bump (batched release).

## Done summary
R5-R6 closed out. Decision record knowledge/decisions/pilot-strike-recovery-is-a-cli-verb-not-2026-08-11 captures the deferred board-native alternative (observed-out-of-ready-since-strike bit) with the tick-granularity hole, the structural-ambiguity argument from the reporter's phase C, and a reopen condition. CHANGELOG Unreleased entry, user-outcome-first, credits @sn-furali (#325). Full gate green; no version bump. The #325 answer is postable by link after merge (tracker-sync.md corrected paragraph + flowctl.md pilot-strikes + troubleshooting entry).
## Evidence
- Commits: 4b9d940c
- Tests: python3 scripts/run_tests_parallel.py (4458 OK), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent)
- PRs: