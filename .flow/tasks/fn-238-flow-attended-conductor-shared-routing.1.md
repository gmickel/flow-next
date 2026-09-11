---
satisfies: [R1, R2, R3, R4, R5, R6, R6a, R7, R8, R9, R10, R11, R12, R13, R14]
---
# fn-238-flow-attended-conductor-shared-routing.1 Implement flow: attended conductor, shared routing reference, opinionated defaults

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Implemented R1-R13 of fn-238: `/flow-next:flow`, the attended conductor, replaces `/flow-next:guide`; six routing reference files under the flow skill (route matrix, spec-count, plan-vs-no-plan, gate selection, prototype-before-ask, tail) are the single copy of the routing rules that capture's closer, plan's next-steps menu, work's zero-task ask, and pipeline-variations now read through step-scoped pointers; direct execution is the default and plan needs a positive signal; `pipeline.qa` accepts `off | on | auto` (schema regenerated, setup asks once, prime names auto, pilot's literal-`on` gate untouched); capture under `from:flow` records `no_plan` when the rule resolves to direct and writes no placeholder coverage table; one read-back contract (`docs/read-back.md`) is shared by capture, interview write-back, and plan's task read-back. Repository docs, changelog (Unreleased), glossary, strategy, conduct index, Codex mirror, AI x SDLC guide, and vault surfaces are updated; the R12 routing-accuracy study ran in agent-evals and ACCEPTED the candidate as non-inferior.

Always-loaded growth (G1): flow SKILL.md is new (about 70 lines: autonomy refusal, mode tokens, six invariants, forbidden list, report shape) and buys the conductor's bounds; capture SKILL.md +6 lines (the exact-token `from:flow` parse) buys the only path by which flow records the route; capture workflow gains a one-paragraph 2.8 route judgment that replaced a ten-line inlined rubric plus a docs link; plan Step 5 gains a ratify-before-write block (plan had no pre-write ask) that runs only interactively; work's rubric copy became a one-line pointer. Everything else is deletion or replacement, and each reference file opens with its decision record.

baseline: red (python3 scripts/run_tests_parallel.py failed pre-edit: 3 test_gate_receipt failures from git 2.55 changing the not-a-repository error text; inherited, unrelated to this task, unchanged after the work); ruff green pre-edit.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: R14 - skipped(deferred: starts after R1-R13 verified and release cut)

Publication state, reported separately from source completion:
- flow-next: committed on branch fn-238-flow-attended-conductor-shared-routing at f4bc2c57, not pushed.
- AI x SDLC guide (~/work/AI-x-SDLC-Starter-Kit): committed locally on branch `flow-next-fn-238-flow` at 238047f, not pushed; navigation check passes.
- Vault (~/work/GordonsVault/Spaces/Projects/flow-next): seven notes plus _index.md and log.md edited in place, `gno index projects` run, retrieval verified for "prototype-before-ask", "attended conductor", "shared routing reference".
- agent-evals (~/work/agent-evals): study `studies/routing-accuracy-2026-09/` committed locally on branch `study/routing-accuracy-2026-09` (bc63d66, 95a7c54, 738c2cb, cffda8a), not pushed; verdict ACCEPTED (DISC replicated: baseline 24/27, candidate 27/27; 90 draws on claude-fable-5-1 at medium effort).
- flow-next.dev: untouched (R14, deferred).

Open items for the conductor:
1. Inherited red baseline: 3 `test_gate_receipt` tests fail on git 2.55 error text ("not a git repository (or any parent up to mount point /)"); outside this spec's Python boundary, needs its own fix.
2. R10 receipts: flow records run-scoped `stage:` lines in its final report, the same convention work and pilot use; `flowctl usage --stages` reads only task-scoped lines from task files, so a QA skip decided by flow after all tasks are done lives in the transcript, not in `usage --stages`. No new machinery was added (spec Boundaries); flag if the reviewer reads R10 more strictly.
3. Setup's Live QA question fires on a first setup run or when the key is absent; existing repos upgrading (key already materialized as `off`) see the value in the summary Notes and the 6c notice instead of a question.
4. Under `from:flow`, capture judges direct-vs-plan at 2.8 (draft time, before the coverage section) and prints the same judgment in the closer; R6 says "at the closer" - same decision, earlier point, needed for R6a.
5. `references/rewrite-mode.md` keeps a one-clause narrative link to `docs/pipeline-variations.md` because `test_install_codex_legacy_cleanup` asserts that rewritten link in the mirror.
6. Study open items: an I22 key-quality question (both arms chose chart where the fixture expects a question), a label-gloss confound declared in the report, and the study branch is based on `factory/no-plan-first-pass-graph`, not `main`.
7. "(next release)" placeholders in docs/README.md Notable updates, release-history.md, the vault notes, and the guide copy need the version number at the release cut.
8. `gno search` cannot match colon-form tokens such as `flow-next:flow`; retrieval was verified with other terms.

stage: impl-review - ran(codex gpt-6-astra, axis: overengineered/non-agentic; round 1 NEEDS_WORK with 3 SHOULD findings fixed in 26079875, round 2 SHIP)
stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: f4bc2c578808d61abccdc98ee47a7de03f8978e2, 26079875
- Tests: python3 scripts/run_tests_parallel.py (post-edit: 3 inherited test_gate_receipt failures only, identical to the pre-edit baseline; every other module green), uvx ruff@0.16.0 check ., python3 scripts/gen_flow_config_schema.py --check, python3 scripts/check_doc_anchors.py, ./scripts/sync-codex.sh (run twice; identical mirror status on the second run), cd plugins/flow-next/tests && python3 -m unittest test_install_codex_legacy_cleanup test_flow_routing test_chart_prompt_scenarios test_chart_docs_inventory test_readback_ask_contract test_pipeline_qa_auto test_command_shim_flatten -q, baseline: red (python3 scripts/run_tests_parallel.py failed pre-edit: 3 test_gate_receipt failures, git 2.55 error text; inherited), stage: impl-review - skipped(policy: host-deferred - conductor owns the gate), stage: R14 - skipped(deferred: starts after R1-R13 verified and release cut), R12 study: ~/work/agent-evals/studies/routing-accuracy-2026-09 (branch study/routing-accuracy-2026-09, ACCEPTED, 90 draws), python3 scripts/run_tests_parallel.py (post-review, HEAD 26079875: 4849 ran, 3 inherited test_gate_receipt failures only, identical to baseline), uvx ruff@0.16.0 check . (post-review: green), python3 scripts/check_doc_anchors.py (post-review: green), ./scripts/sync-codex.sh (post-review, run twice: idempotent), cd plugins/flow-next/tests && python3 -m unittest test_flow_routing test_chart_docs_inventory test_chart_prompt_scenarios test_readback_ask_contract test_install_codex_legacy_cleanup test_pipeline_qa_auto -q (post-review: 84 OK), stage: impl-review - ran(codex exec read-only, gpt-6-astra high, sub2 instance, axis: overengineered/non-agentic): round 1 NEEDS_WORK (3 SHOULD) -> fix 26079875 -> round 2 SHIP; receipts .flow/tmp/codex-review/fn-238-review.md, fn-238-rereview.md, stage: plan-sync - skipped(config: planSync.enabled != true)
- PRs: