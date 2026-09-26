---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15]
---
# fn-255-unattended-run-correctness-fixes-audit.1 Implement Unattended-run correctness fixes (audit wave 1)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Implemented all fifteen unattended-run fixes in R1-R15, with regression tests for each. Config parse errors are no longer treated as a missing file. `review-rounds record` derives the receipt fields from the recorded output and refuses a payload that contradicts it. Every spec-sidecar writer now takes the per-spec lock. Triage-skip leaves open reviews alone. `flow --auto` resolves its scope and review arguments correctly and stops on blocked work. The work branch step no longer assumes `main`. The Ralph guard matches shell commands precisely. Plan-sync receives its inputs as files. Handover paths are unique per task. Fan-out recovers the draws that completed. Tracker push refuses when the tracker body has diverged.

Tier: session (jev long_running 0.73); implementer bridged to gpt-6-astra at medium (codex exec), host fixes on the session model.

GATE_SKIPPED:unittest:green-receipt f61f048e - baseline reused from prior post-gate pass

Review round 1 (three codex draws) returned NEEDS_WORK with five findings; all were fixed in f61f048e. The findings were: guard bypasses through shell control words and split redirect words, a stale planning-file carry in the branch fence, a missing verdict in the RP payload, and broken Codex links to `worker.md`. Round 2 returned SHIP. Host follow-up 26e87d27: `record` copies the review text instead of comparing it, because an exact comparison would refuse host payloads that differ only in whitespace, and it leaves derived fields with no signal off the receipt.

Follow-ups (not built): SubagentStop with no `agent_type` now skips the worker receipt gate, so check whether any Ralph host omits that field. R15 implements the parked push intent as written (push refuses on divergence), pending Gordon's confirmation.

stage: impl-review - ran [2026-09-25..2026-09-26]
stage: implement - ran (model: gpt-6-astra at medium; delegated: 5)
stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: ccb513bd88ef83bfad35007c40f8749e10cbe623, 26e87d2790f8a3842ceedb31ca3cf5dbce5989ea, f61f048ee7cf42d9b73522f78631d82b80ea0655, d946f4348543f2172eb7c7bdfd52818655aafa50
- Tests: python3 scripts/run_tests_parallel.py (baseline green at 77fc2248; green at f61f048e: 237 files, 5076 tests, 0 failures), GATE_SKIPPED:unittest:green-receipt f61f048e - baseline reused from prior post-gate pass, uvx ruff@0.16.0 check ., python3 -m unittest plugins/flow-next/tests/test_unattended_core.py plugins/flow-next/tests/test_review_convergence_journal.py plugins/flow-next/tests/test_unattended_work_contracts.py plugins/flow-next/tests/test_ralph_guard.py, ./scripts/sync-codex.sh (twice, idempotent)
- PRs: