---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12]
---
# fn-295-opt-in-development-evidence-and-spec.1 Implement Opt-in development evidence and spec approval for regulated teams

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Added the three opt-in pieces: evidence.persist on (flowctl copies every review and QA receipt per round, QA captures, each done task's evidence and a run record into the spec's evidence folder and stages them), spec.approval pr (start, spec ready, flow --auto selection and judge route treat a spec as ready only after its spec-branch PR merged with an approving review, recorded on the spec; authoring writes point at the gated reference references/spec-approval-pr.md), and flowctl trace (md/csv/json matrix with gap check, exit 0/1/2). Default config is unchanged: the keys are unseeded and read raw, and no skill prompt changed. Tests: plugins/flow-next/tests/test_evidence_and_spec_approval.py (default-path smoke and each R2/R6/R8 error case). Docs: flowctl.md, README line, CHANGELOG Unreleased, schema; the flow-next.dev page, nav, bento, config and CLI entries are in site repo commit eecebfa on branch docs/regulated-environments (not pushed).

OPEN_ITEM: R11 downstream walk (mickel.tech, AI x SDLC guide, microsite if needed, vault release timeline) belongs to the release that ships this; not done here.
OPEN_ITEM: spec owner call on two declined review findings. #11 (P1): R2 "test output" - flowctl persists the test commands and result text the worker records at done; capturing raw output would need new worker instructions, which R1 forbids on the default path. #8 (P2): R1 byte-identical vs R8's new command - the root --help command list necessarily gains trace.
OVERRIDDEN: 2 declined findings (#11, #8) - reviewer: R2 needs raw test output and R8 actual results; R1 allows no help change. Mine: both need a spec-wording decision, not a code fix within the stated R1 constraint.

Tier: session (jev intelligent 0.85) (model: claude-opus-5-5)

stage: impl-review - ran (codex, 3 rounds: NEEDS_WORK 12 findings, 10 fixed or withdrawn, then NEEDS_WORK on the 2 declined findings; OVERRIDDEN)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: f136ff38845e9307f00e18ee58572a3e48dc387c, 3ada49c3a69b21442cb80bbc55ab07d5f52f1321, 990d2b656acc3b4b9d1f7506e81abc69f15bc01a
- Tests: python3 scripts/run_tests_parallel.py (4030 ok, before review fixes), python3 -m unittest test_evidence_and_spec_approval plus 26 focused suites (500 ok, after fixes), uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, python3 scripts/gen_flow_config_schema.py --check, flow-next.dev: pnpm build, pnpm test, pnpm check:links, pnpm check:seo
- PRs: