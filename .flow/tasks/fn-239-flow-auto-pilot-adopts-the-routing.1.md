---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14]
---
# fn-239-flow-auto-pilot-adopts-the-routing.1 Implement flow --auto: pilot adopts the routing reference and runs long-horizon over the same rails

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
`/flow-next:flow --auto` is now the unattended driver: pilot's guards, rails, selection, PR probe, branch matrix, strikes ledger, and decision log moved into the gated `skills/flow-next-flow/auto.md`, its stage table was replaced by reads of `route-matrix.md`, `plan-vs-no-plan.md`, and `gate-selection.md`, and the hop loop drives one ready item to a terminal (`--tick` runs one hop). `/flow-next:pilot` stays one release as a command shim and skill stub onto `flow --auto --tick`; `pipeline.chainStages` is honoured only under `--tick` and deprecated with the alias; `pipeline.qa=auto` takes effect unattended; a zero-task ready spec has its route recorded before mint; attended flow keeps its refusal under every marker while `--auto` refuses only under Ralph.

Coverage of the acceptance criteria: R1 to R11 and R13 are shipped in commit 8ebb5974 (auto.md, SKILL.md tokens and inverted refusal, the moved references, the shim and stub, schema and sync roster, tests re-pointed plus `test_flow_auto.py`, Codex mirror regenerated twice with no diff, repository docs and skill prose, conduct rows). R12 is scaffolded, not run: `~/work/agent-evals/studies/long-horizon-auto-2026-09/` (commit e1d58df on branch `study/routing-accuracy-2026-09`, the branch that was checked out there) holds the pre-registration, the parity extractor with 16 passing tests, the runner outline, and a report stub; the draws need a terminal-driven `claude -p` run against the finished branch and are the remaining work. R14 (flow-next.dev) is deferred by the spec's own rule until the release is cut. The AI x SDLC guide (commit ab0d6fc on main, not pushed) and the vault flow-next space (10 notes, reindexed) are updated.

Follow-ups noted, not built: pre-existing em dashes survive on docs lines that received in-line substring swaps (724 test pins carry them); the guide still says "upcoming release" for the 5.0 attended conductor in untouched paragraphs; vault notes `Project Overview` and `Teams & Adoption` keep older pilot context; `release-history.md` and the site version constant are stamped at release time.

Tests: full suite `python3 scripts/run_tests_parallel.py` green (4889 ran, 0 failures, 6 skipped) and `uvx ruff@0.16.0 check .` clean at 8ebb5974; baseline before edits was green (4866 ran). Gate receipt written for the unittest gate. Errors the ACs enumerate are covered by `test_flow_auto.py` (Ralph refusal exits 1 with the exact verdict, FLOW_AUTONOMOUS alone passes, lookalike flags rejected, chainStages ignored with a stderr notice in long-horizon mode) and `test_pipeline_qa_auto.py` (the three qa values plus two invalid ones).

stage: impl-review - skipped(config: REVIEW_MODE=none)
## Evidence
- Commits: 8ebb5974c7635d09e9166320fd80adb0037aac2f
- Tests: baseline: green (python3 scripts/run_tests_parallel.py: 4866 ran, 0 failures; uvx ruff@0.16.0 check .: clean), python3 scripts/run_tests_parallel.py (verify: 4889 ran, 0 failures, 6 skipped; GREEN_RECEIPT .flow/tmp/green-receipts/8ebb5974-unittest.json), uvx ruff@0.16.0 check ., python3 scripts/gen_flow_config_schema.py --check, ./scripts/sync-codex.sh x2 (no diff on the second run), python3 -m unittest test_flow_auto test_flow_routing test_pipeline_qa_auto test_pilot_chain_stages test_pilot_strikes_prose test_pilot_backlog_mirror_safety test_tracker_sync_backlog_mode test_skill_prose_diet test_ralph_guard test_precheck_mode_contract test_command_shim_flatten test_stage_model_provenance test_install_codex_legacy_cleanup (265 ran), python3 scripts/check_doc_anchors.py, agent-evals: python3 studies/long-horizon-auto-2026-09/scripts/parity.py selftest (16 pass)
- PRs: