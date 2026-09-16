---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-246-evaluate-typesafe-jev-as-a-judge-for.1 Implement Evaluate TypeSafe Jev as a judge for flow's pipeline-variation decisions

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Built a stdlib Jev judge harness outside the shipped product, ran it over 49 samples (36 specs across flow-next/dettivo-linux/flow-swarm with flow-next capped at one third, plus 13 authored intents) for all five pipeline-variation sites, labeled every sample once with the session model (scouts that never saw Jev output), and rendered the directional report. Report: ~/work/agent-evals/studies/jev-pipeline-judge-2026-09/report.md (commit 12bd1e2 in agent-evals); this branch carries only .flow state (R8).

Result in one line per site: route one-call 0.59 agreement (drop), route two-phase 0.65 with label in Jev's top three 45/49 (needs-more-signal; the `brief` view's capture-vs-ready ambiguity accounts for most misses), plan-vs-no-plan 0.80 (keep), spec-count 0.59 (drop; `multiple_shippable_outcomes` over-trips), fork classification 0.71 with confidence separating cleanly 0.72 vs 0.35 (needs-more-signal), QA gate 0.86 (keep). Every state fit the 32k budget (max 14.3k input tokens, median 2.9k); median latency ~650 ms; zero unassembled, aborted, or unlabeled samples.

Follow-ups noted, not built: tighten the `user_asked_for_plan` instruction to an explicit ask; drop the `brief` view or make the intake/ready distinction a state field; add a confidence floor before fork_class is trusted.

stage: impl-review - skipped(config: REVIEW_MODE=none)
## Evidence
- Commits: c5b07be2a6a6087591472891297778acc16d3c0d
- Tests: baseline: none (spec defines no Quick commands), python3 harness.py presets (five presets loaded, option sets verbatim from routing references, >=2 options each), python3 harness.py assemble (49 states, 0 unassembled), python3 harness.py run (98 Jev calls, 0 aborted, 0 over budget), python3 report.py (report.md rendered; 49/49 labeled), flowctl gate classify --base 07905c2c36b6f96eea815e120e117fff6d2bc8dc -> TIER_B docs-only; no test/smoke gates defined by the spec, external evidence commit: agent-evals 12bd1e2 studies/jev-pipeline-judge-2026-09
- PRs: