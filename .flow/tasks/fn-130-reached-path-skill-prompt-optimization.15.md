---
satisfies: [R2, R4, R5, R6, R7, R8, R9, R10, R12, R14]
---
# fn-130-reached-path-skill-prompt-optimization.15 Run canonical Claude skill fleet smoke

## Description
Run the actual B1 and candidate Claude plugins through `claude --plugin-dir` in
disposable git repositories. Exercise each optimized user workflow through its
real skill-discovery/invocation surface, then compare terminal output, Flow
state, repository effects, receipts, and safety boundaries. This supplements
the injected-prompt agentic evidence with canonical plugin execution.

## Acceptance
- [ ] Materialize immutable B1 and current candidate plugin roots with hashes.
- [ ] Safe-mode Claude loads only the explicit plugin root; no installed Flow-Next plugin wins discovery.
- [ ] Baseline and candidate invoke Plan, Setup, Tracker Sync, Prime, Plan Review, Work, Strategy, Make PR, and Pilot through their real `/flow-next:*` skill surface.
- [ ] Fixtures run only in disposable repositories; tracker/PR scenarios do not mutate live services.
- [ ] Captured transcripts, repository diffs, Flow state, receipts, usage, model/CLI provenance, and per-case checks are retained.
- [ ] Candidate meets or exceeds the B1 behavioral contract on every case; any intentional version-contract difference is explicit.
- [ ] Harness self-tests, focused tests, full suite, mirror sync, and plugin smoke pass.

## Quick commands

```bash
python3 optimization/reached-path/run_claude_fleet_smoke.py --all
python3 -m unittest -q test_fn130_claude_fleet_smoke
python3 scripts/run_tests_parallel.py
```

## Done summary
Ran the actual immutable B1 and current canonical Claude plugins across all nine optimized workflows. Candidate passed 9/9, retained every B1 pass, and repaired the observed Plan drift-warning and Plan Review foreground-export misses. Added a sanitized reusable harness, explicit Plan manifest read, durable evidence, and closure documentation.
## Evidence
- Commits: 53180df7
- Tests: python3 optimization/reached-path/run_claude_fleet_smoke.py --all --workers 3, python3 -m unittest -q test_fn130_claude_fleet_smoke test_precheck_mode_contract, python3 -m unittest -q test_fn130_claude_fleet_smoke test_precheck_mode_contract test_skill_prose_diet test_token_budgets test_setup_cursor_host test_setup_grok_host test_model_routing_scaffold test_prime_eval test_backend_spec test_parallel_work_prose test_pilot_backlog_mirror_safety test_tracker_sync_state test_tracker_sync_mirror_parity test_tracker_sync_gitlab test_tracker_sync_jira, python3 scripts/run_tests_parallel.py, bash plugins/flow-next/scripts/smoke_test.sh, ./scripts/sync-codex.sh (idempotent hash check), artifact privacy grep + promotion jq
- PRs: