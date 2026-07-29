---
satisfies: [R14, R15]
---
# fn-141-tracker-determinism-c-prose-teardown.5 Re-freeze fn-130 tracker baselines with enumerated fixtures + delta

## Description
**Do NOT re-freeze B1.** `freeze_b1()` refuses a non-empty destination because B1 is write-once and hash-addressed; overwriting it destroys the provenance the delta is measured against. fn-134 updated **candidate** evidence, not B1 - follow that precedent.

Record the reduction as a **candidate delta**, naming every affected tracker fixture explicitly. If a genuinely new baseline is wanted, that is a deliberate **B2** with its own commit/tag, inventory constant, validator, lineage and migration rationale - never an in-place overwrite.

Runs after the canonical skill and caller edits (.2) and their behavioral verification (.3), so it never measures an intermediate tree or races generated mirror edits.

## Acceptance
- [ ] B1 left untouched; reduction recorded as a CANDIDATE delta
- [ ] Every affected tracker fixture enumerated by name
- [ ] Before/after delta recorded as an artifact
- [ ] Rationale recorded: reduction by design, not regression
- [ ] If a B2 is introduced instead, it carries commit/tag, inventory constant, validator and lineage
- [ ] Reached-path harness green
- [ ] sync-codex.sh run twice, mirror committed

## Done summary
Recorded the fn-141 tracker prose reduction as a reproducible CANDIDATE delta without modifying immutable B1 or introducing B2. The artifact explicitly enumerates all 15 tracker fixtures, records 452,552 to 135,344 characters per fixture, and states that the 70.09% reduction is by design rather than a regression. Added a generator, a harness freshness/completeness guard, and reached-path documentation; sync-codex ran twice with identical results.
## Evidence
- Commits: bbd628833524be56115c67c12fbee17293715b70
- Tests: baseline: green via honored unittest receipt 05d42c33, cd plugins/flow-next/tests && python3 -m unittest test_tracker_sync_mirror_parity test_reached_path_harness -q, python3 -m unittest discover -s plugins/flow-next/tests -p 'test_tracker_sync_routing.py' -q, python3 optimization/reached-path/tracker_candidate.py --source-commit 6556237767bb216b650a78cb05bef769b84b32eb --check, python3 optimization/reached-path/run_eval.py --validate-b1, uvx ruff@0.16.0 check optimization/reached-path/tracker_candidate.py plugins/flow-next/tests/test_reached_path_harness.py, ./scripts/sync-codex.sh twice; status snapshots identical
- PRs:
