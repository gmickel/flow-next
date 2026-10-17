---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-298-measured-numbers-you-can-trust-limiter.1 Implement Measured numbers you can trust: limiter, errors, work done

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
One gated reference, `plugins/flow-next/references/measured-numbers.md`, holds the checks a reported number passes before anyone acts on it: the limiter from a profile or counters of a real run, the alternatives ruled out (fast errors, warm cache on one side, work outside the timed region, untuned side, noise, too small to matter), share-of-run arithmetic, that the work happened, five or more alternated runs per side with median and range, every side tuned as production runs it; the four verdicts (`faster`, `slower`, `no measurable difference`, `inconclusive`), the unprofilable-metric and one-run-ballpark rules, the eval-draw completion rule, and the evidence line. Readers: the slowness row (route-matrix.md) and the implementer paths that take that measurement (work phases.md step 3, worker.md Phase 1.5 item 5, worker-bridge.md pointer list), hill-climb.md (harness setup and the final claim), and measure-behaviour-change.md (the verdict carries the completion count). Hill climb: the harness prints error and work counts next to the metric and treats fewer units of work or a new error as a wrong output (more completed work counts as a gain); the proof runs contrasting realistic workloads and fixes the reproduction or stops when no case reproduces the complaint; families run cheapest first; the record carries the limiter and the counts. A contract test pins the reference's reader set. pipeline-variations.md, CHANGELOG Unreleased, the Codex mirror, and flow-next.dev (local branch `docs/fn-298-measured-numbers`, ce97634, not pushed: held for the release with the other specs in this set) are updated.

R6 (measured, same-time A/B in the maintainer's comparison harness, A = main 1d10c8f7, B = ada04185, 3 attended draws per arm, run under the shared wall-clock lock):
- New case `ledgerlite-perf` (synthetic Python CLI that caches parsed exports; local re-run 0.36 s vs the 2.5 s cold run CI pays, so an uncontrolled before/after shows ~7x). Graded on the first hand-back per a preregistration written before the draws: B reported cold-against-cold numbers and named the CI cold path in 3/3 draws, no draw claimed the warm-cache speedup, and B read the reference in 3/3. A did the same in 3/3, so the case does not separate the arms; what B added was alternated runs (3/3 vs 0/3), a named limiter with share-of-run arithmetic, and explicit errors/work-done checks. First hand-back on the new case: A median 162 s, B 197 s; cost +$0.11 per draw. All 6 draws pass the hidden byte-identity check; judge 16-17 (A), 17 (B).
- Existing cases, first hand-back: gno-187 A 117.5 s (78-184) vs B 139.6 s (118-159); flow-swarm-211 A 292.9 s (122-311) vs B 272.3 s (115-340). Both gaps inside the run-to-run spread: no measurable difference. Walls B ≤ A on both medians; all 12 draws pass hidden checks; judge equal or higher on B.
- Case defect found: `ledger` was committed without the exec bit, which every draw noticed and the simulated person asked to fix in 4/6 draws, after the graded hand-back and equally in both arms.

Decisions:
- R6's existing-case clause read as met: gno-187's +22 s median sits inside both arms' ranges (n=3), and the only fn-298 text a defect draw sees is one sentence in the route matrix; turn counts match. A further replicate would have queued behind two other sessions' timed evals.
- The reference's worked example uses an untuned-side comparison, not a warm cache, so the R6 case does not test the example text.

stage: impl-review - ran [round 1 NEEDS_WORK (one finding, all three lenses: keep rule rejected throughput gains; fixed in ada04185), re-review SHIP at ada04185 with R6 deferred pending the eval] (model: codex gpt-6-astra high)
stage: plan-sync - skipped(config: single implicit-owner task, no downstream tasks)
## Evidence
- Commits: 8af12d9e9bd39669aaaa7294b4ac0d900eca4ecc, ada0418530e01c93ecb67b8a5767c541e4d9bb5e
- Tests: cd plugins/flow-next/tests && uv run --with pytest python -m pytest -q test_flow_routing.py test_shipped_links.py test_sync_codex_check.py test_reference_encoding_guard.py test_skill_prose_flowctl_surface.py test_skill_prose_diet.py test_pr_cognitive_aid*.py test_export_cognitive_aid.py (135 passed), python3 scripts/run_tests_parallel.py (4053 ran, 0 failures), uvx ruff@0.16.0 check . (clean), fn271 rounds fn298r6-{ledgerlite-perf,gno-187,flow-swarm-211}-{A,B}-1016: same-time A/B, 3 draws per arm
- PRs: