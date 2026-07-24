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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
