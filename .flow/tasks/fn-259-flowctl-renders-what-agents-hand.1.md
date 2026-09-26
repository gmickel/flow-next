---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31]
---
# fn-259-flowctl-renders-what-agents-hand.1 Implement flowctl renders what agents hand-assemble (audit wave 5)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Implemented all 31 fn-259 R-IDs: flowctl now renders, validates, counts and joins what skills used to hand-assemble (pilot snapshot and strike record, ready admission, done --range, tier/sync-active joins, review-prompt / record --attach / increment ranges / resume-terminal / fan-out merge-plan, tracker render / prepare / call diet, bulk task create, validate coverage, preflight, prospect write, qa receipt, memory audit-scan / apply / check-overlap, setup-status, bundled make-pr and map scripts, lazy imports), and the consuming skills call those verbs. Evidence per R-ID is in `.flow/artifacts/fn-259-implementation/README.md`.

stage: implement - ran (model: gpt-6-astra at medium; delegated: 12)
stage: impl-review - ran [round 1 fan-out NEEDS_WORK (5 introduced) .. round 2 SHIP; post-SHIP delta review of 68e0aec8 SHIP]
stage: plan-sync - skipped(config: planSync.enabled != true)

Spec drift: no R-ID was already fully met by waves 1-4. Parts already present were reused, not rebuilt: plan and completion default receipts (e5535836, R14), Linear parent state fields (e6a86018, R18), and wave-1 `review-rounds record` derivation (b4c980af).

Host fixes after the bridge (range check and review):
- The pilot snapshot joins open PRs from one open-state listing. Only the selected branch gets the full-history probe. The first version listed every PR and failed closed at 1000 rows. Observations for the other candidates are marked `history_complete: false` and get no lifecycle decision. auto.md refreshes a reselected candidate with `pilot snapshot --spec`.
- Completion review's Step 0.5 again prints the exact `ESCALATE: reviewer requested human review` line that ralph.sh greps for.
- The dirty-tree guard prints the dirty paths again.
- Backlog's direct wire reads pass the durable/display JSON locator.
- `qa receipt` accepts tracker spec ids.
- `review-prompt plan` needs no `main` branch.
- A rendered push body keeps the paired-base echo fence.
- A make-pr dry run accepts a commit-SHA `--base`.

Error-case tests: R2 `test_judge_consumers` (unavailable judge keeps lifecycle; probe failure gives no guess), R3 `test_pilot_snapshot`, R4 `test_pilot_snapshot` (unknown spec, concurrent records), R10/R11/R12 `test_scheduler_plumbing` (touches-missing, unreachable range SHA, unknown task, inactive tracker), R13 `test_review_findings_parse_status`, R14 `test_review_render_commands`, R15 `test_resume_terminal` (unknown state fails closed), R16 `test_review_fanout` (missing refs), R17/R19 `test_tracker_preparation`, R18 `test_tracker_facade` call-count matrix, R21 `test_task_bulk_create`, R22/R23 `test_planning_preflight`, R25/R26 `test_artifact_writers`, R27/R28 `test_memory_audit_bundle`, R29 `test_setup_status`, R30 `test_bundled_map`.

Open acceptance evidence:
- R1: the macOS and Windows legs need CI; nothing was pushed. Linux suite, Ruff, mirror and offline smokes are green.
- R7: six runs per arm. Median output tokens 13,097 before vs 12,117 after (down 7.5%). Median tool calls 13.5 vs 14.5 (mean 15.2 vs 14.0). The "no increase in median tool calls" half is not demonstrated.
- R13: the audit's six literal draw artifacts were not available. The parser handles six representative shapes, and the three real wave-4 draws on disk parse.
- R31: module import is 23.5% faster; end-to-end `--help` is unchanged.

Follow-ups (not built): a live make-pr run still cannot take a SHA base (a GitHub base must be a branch). This is pre-existing behavior.

GATE_SKIPPED:unittest:green-receipt 68e0aec8 - baseline reused from prior post-gate pass
## Evidence
- Commits: 988ebf95a22a2e84eca97f40b295562cc36503c9, ae575ed2c5708597b1865a54ce98295096dfdde1, 1a8d18a0578ca651be0503642d071e1be9faf53b, c5e10707954b08d615b9591edb4269e2fca39a84, b05a87bfc1a5a551975ec2caebe05a55b5482d34, 68e0aec8c7243e732493c07a2af2baa723765379, 2c64ad19dac114a5ad86452edb1a83b0c2cf056e
- Tests: baseline: green (python3 scripts/run_tests_parallel.py 5125 ran pre-edit; uvx ruff@0.16.0 check . clean), python3 scripts/run_tests_parallel.py (final 5201 ran, 0 failures, green receipt 68e0aec8), GATE_SKIPPED:unittest:green-receipt 68e0aec8 - baseline reused from prior post-gate pass, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh (x2) and ./scripts/sync-codex.sh --check, python3 scripts/check_doc_anchors.py, git diff --check fc93b0a4..HEAD, PATH=/usr/bin:/bin smoke_test.sh (128 pass), impl-review_smoke_test.sh (71 pass), make-pr_smoke_test.sh (63 pass), map_smoke_test.sh, prospect_smoke_test.sh, audit_smoke_test.sh, plan_review_prompt_smoke.sh INCONCLUSIVE: live claude+RepoPrompt smoke, RepoPrompt unavailable on Linux, make-pr measurement: .flow/artifacts/fn-249-make-pr-measurement/measure.sh x6 per arm (p5 before, p6 after, p7 after SHA-base fix), focused: test_pilot_snapshot test_host_review_backend test_tracker_preparation test_review_render_commands test_artifact_writers test_tracker_sync_backlog_mode test_bundled_make_pr test_review_prompt_constraints
- PRs: