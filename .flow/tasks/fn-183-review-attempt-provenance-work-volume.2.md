---
satisfies: [R4]
---
# fn-183-review-attempt-provenance-work-volume.2 Read surface: attempts --json exposes new fields; old rows tolerated

## Description
Spec fn-183 (#312). review-rounds attempts --json surfaces the new fields; rows written by older versions read back with fields absent (unknown, never zero) and no crash.

**Files:** plugins/flow-next/scripts/flowctl.py (`cmd_review_rounds_attempts`) + `.flow/bin/flowctl.py` dual copy; read-surface tests

## Acceptance
R4 of the spec.

## Done summary
R4 verified end-to-end through the real CLI (argparse -> cmd_review_rounds_attempts -> _review_attempt_summary -> json_output): rows return unprojected, so the .1 fields already surface. No code gap; pinned with 5 CLI-level tests (TestAttemptsReadSurface): writer-to-reader fallback fixture, snapshot row surfaces all four fields, measured tool_calls=0 survives read (falsy-drop guard), pre-fn-183 legacy rows read back with fields absent (assertNotIn) and exit 0 on both --json and human paths, mixed ledger clean. Mutation check confirmed tests fail if the read path starts projecting keys. Tests-only commit, no propagation needed.
## Evidence
- Commits: 0f1a016e
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap -q (182 OK)
- PRs: