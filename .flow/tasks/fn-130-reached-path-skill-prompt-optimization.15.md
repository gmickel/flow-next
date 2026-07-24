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
Ran immutable B1 and current canonical Claude plugins across all nine optimized workflows: candidate 9/9, B1 7/9, no candidate regression. Repaired Plan's explicit manifest read, then fixed the independent reviewer's Codex installer-path finding. An official temporary Codex install emitted the exact 0.0.1 to 3.4.1 warning and completed planning. Sol High completion re-review: SHIP.
## Evidence
- Commits: 53180df7, b0c69668
- Tests: python3 optimization/reached-path/run_claude_fleet_smoke.py --all --workers 3; official temporary install-codex.sh + actual codex exec $flow-next-plan copy-mode mismatch smoke; python3 -m unittest -q test_precheck_mode_contract test_sync_check test_fn130_claude_fleet_smoke; python3 scripts/run_tests_parallel.py (2298 passed, 3 skipped); bash plugins/flow-next/scripts/smoke_test.sh (136 passed); scripts/sync-codex.sh idempotent + manifest-path hard-fail; artifact privacy grep + promotion jq; gpt-5.6-sol high completion review: SHIP
- PRs:
