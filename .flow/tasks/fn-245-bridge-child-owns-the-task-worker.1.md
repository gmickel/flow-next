---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11]
---
# fn-245-bridge-child-owns-the-task-worker.1 Implement Bridge child owns the task: worker bridge path, fan-out license restored, July codex caveats retired

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
The worker agent definition gains Phase 1b, a bridged-implementer path that hands the task to the child when the implementer tier resolves to a CLI-reached model (pointer prompt plus the usage guide's brief, one foreground bridge call, dirty-remainder commit, base..HEAD range review, focused gates, then Phase 3; `stage: implement` records the command-line model and the digest's delegation count). The long-task brief's never clause now reads "never spawn another bridge" and carries the judicious-subagent license; the July "keep the child flat" caveats and fn-98's stale steering caveats are dated watch lines and measured facts (usage.md, codex reach page, platforms.md); fn-98 is closed with a pointer; STRATEGY.md gains "The owner holds the license", .flow/criteria.md gains G3, two bug memory entries and the CHANGELOG Unreleased entry record the change; the Codex mirror is regenerated idempotently.

R-ID notes: R2's Codex mirror carries the implementer-tier paragraph and the new one, both grep-guarded in sync-codex.sh (with the optional `IMPLEMENTER` dispatch line the review added). R4's usage.md watch line names versions, counts, date and issue while the model identifier lives on the codex reach page (usage.md stays identifier-free per fn-195 R2's guard test; the reach page carries `gpt-6-astra`). R5: orchestration.md and the setup model-routing snippet carried no unreliable-steering caveat at close time (grep clean), so only the reach page, platforms.md, and usage.md changed; fn-98's R4 and R5-R9 are recorded as undone in its close addendum. R10's site half (work page, model-routing guide, cookbook entry, landing card on flow-next.dev) is release-walk follow-up in the separate site repo, not done here. Follow-up noted, not built: the owner-serial versus owner-delegating eval under agent-evals.

baseline: green (python3 scripts/run_tests_parallel.py, 4991 ran pre-edit)
verify: gate classify FULL (force-full prefix plugins/flow-next/agents/); python3 scripts/run_tests_parallel.py green at 79bc5ad9 (4991 ran); uvx ruff@0.16.0 check . clean; sync-codex.sh twice, clean second diff; green receipt .flow/tmp/green-receipts/79bc5ad9-unittest.json

stage: impl-review - ran (codex, three-draw fan-out round 1 NEEDS_WORK with 3 merged findings, fixed in f5d0a877; single-dispatch round 2 SHIP)
## Evidence
- Commits: aaba15d0290b7a2213ae83507b72287c7917fa4a, f5d0a87722dbe98b97074a307cb546c5b53e896a, 79bc5ad9cfceb92dbdb684e082bf26e8d2f63b84
- Tests: python3 scripts/run_tests_parallel.py (baseline: green pre-edit, 4991 ran; verify: green at 79bc5ad9, 4991 ran, receipt .flow/tmp/green-receipts/79bc5ad9-unittest.json), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent, clean second diff), python3 -m unittest test_worker_anchor_prose test_skill_prose_diet test_cmd_usage test_criteria test_gate_classify test_parallel_work_prose test_setup_reference_routing (146 ok)
- PRs: