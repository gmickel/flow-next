---
satisfies: [R1, R2, R3, R4]
---
# fn-304-honor-copilot-reasoning-effort-for.1 Pass supported Copilot reasoning effort without family omissions

## Description
# Copilot Claude effort dispatch

### Problem

`run_copilot_exec` currently omits reasoning effort for Claude-family models and sends OpenAI-family models the `--effort` option. The installed GitHub Copilot CLI 1.0.98 help exposes `--reasoning-effort` with `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`. As a result, a resolved Claude effort such as `high` is not delivered to the CLI, while the existing OpenAI dispatch option does not match the installed CLI contract.

Copilot review sessions deny shell access while shared prompts ask the reviewer to inspect the Git diff. Review run `RID6e3c4750889e48ffa25228bb5eb678dc` over `627efd03862b663482ec34a66d7559f482a14529..b5d103c1bddec7c114926108c5795ee29adb3799` returned three mechanical `SHIP` verdicts without any reviewer reading the patch. The recorded run has no diff coverage and is incomplete; Copilot primary reviews and fanout draws need the pinned diff at a readable path, with instructions to use available read-only file tools. Claude's current diff delivery remains supported.

### Acceptance criteria

- **R1:** For Claude-family and OpenAI-family models, dispatch the resolved effort, including `high`, using the CLI-supported `--reasoning-effort` option.
- **R2:** At the model-resolution floor, omit `--reasoning-effort` and keep the receipt truthful about the effective model and effort.
- **R3:** Preserve read-only tool restrictions, POSIX and Windows prompt delivery, first-call and resumed session behavior, model-unavailable fallback classification, and accurate receipts for non-floor dispatches.
- **R4:** Deliver the exact pinned diff by readable file for Copilot primary implementation, plan, and completion reviews and implementation fanout draws. Materialize it before managed or CLI dispatch, retain receipt and range identity, direct Copilot to available read-only file tools while shell is denied, fail closed before dispatch if materialization fails, and preserve Claude transport behavior.

## Acceptance
- [ ] Copilot primary implementation, plan, and completion dispatches materialize the exact reviewed base-to-head diff before execution and identify the readable file in the prompt.
- [ ] Every Copilot implementation fanout draw retains its receipt, range, and axis identity in the materialized diff path.
- [ ] Copilot transport instructions accurately describe denied shell/write tools and direct the reviewer to read the file with available read-only tools.
- [ ] Diff materialization failures stop before managed or CLI execution, while existing Claude diff transport, guards, and path identity remain unchanged.

## Done summary
# Task handoff: Copilot reasoning effort and pinned review diffs

### Implementation status

The implementation is complete at source revision `97f0cd4a8e4ebc7c3665ff975358d2d0c571b0bc`. This follow-up addresses the final implementation review's introduced P3 documentation omission in the two canonical docs and their generated Codex mirrors. No Python behavior, tests, spec state, or task state changed in this follow-up.

### Acceptance coverage

| Requirement | Evidence |
| --- | --- |
| R1 | Copilot sends the resolved `--reasoning-effort` for supported Claude-family and OpenAI-family models, including `high`. The implementation review verified `run_copilot_exec` and coverage for Claude Opus, Haiku, and GPT. |
| R2 | The `auto` fallback floor omits `--reasoning-effort`; its receipt and attempt row omit the unselected effort. `test_floor_uses_auto_and_omits_reasoning_effort` covers this. |
| R3 | Shell/write denials, POSIX argv and Windows stdin prompt delivery, create/resume markers, model-unavailable fallback classification, and non-floor receipts remain covered by source tests. |
| R4 | Primary implementation, plan, and completion reviews plus every implementation fan-out draw receive the complete pinned diff by readable path before dispatch. Failed materialization stops before managed or CLI dispatch. The current docs name the path and the read-only file-viewing tools while preserving shell/write denials. |

### Review record

- Official implementation review run `5388114c8c654382b763cc413d9b7cc6` returned `SHIP` from independent correctness, contracts, and integration sessions.
- Exact reviewed range: `627efd03862b663482ec34a66d7559f482a14529..97f0cd4a8e4ebc7c3665ff975358d2d0c571b0bc`.
- The review evidence records all three sessions reading byte-equal views of the complete 38,696-byte pinned diff and assessing R1-R4 across all nine source paths. Reviewers did not run tests.
- The earlier run `6e3c4750889e48ffa25228bb5eb678dc` recorded a mechanical `SHIP` but the sessions read no patch because shell access was denied. Its preserved receipt is incomplete and was not accepted as review coverage.
- Final review finding: introduced P3 at `plugins/flow-next/docs/flowctl.md` and `plugins/flow-next/skills/flow-next-impl-review/workflow-cli.md`; addressed by this documentation follow-up.
- The pre-existing P3 about the opt-in Copilot triage judge's older effort flag is outside this task and remains untouched.

### Documentation follow-up

Updated the Copilot backend entries in `plugins/flow-next/docs/flowctl.md` and `plugins/flow-next/skills/flow-next-impl-review/workflow-cli.md`. Both now describe the pinned diff under `.flow/tmp/claude-review/`, the available read-only file-viewing tools, denied shell/write access, and failure before dispatch. `scripts/sync-codex.sh` generated the corresponding two Codex mirror updates.

The existing flow-next.dev Copilot paragraph is at [Review backends, Per-backend notes](https://flow-next.dev/reference/review-backends/). It currently states the read-only tool restriction but omits pinned-diff delivery. No local website source checkout was available in this worktree or the bounded Dev/Worktrees search, so no site edit or publication was made; root can inspect site ownership for a separate source update.

### Validation

- Source freeze at `97f0cd4a8e4ebc7c3665ff975358d2d0c571b0bc`: preserved `python3 scripts/run_tests_parallel.py` log reports 4045 tests, 0 failures, 0 errors, and 7 skipped. The source Ruff and mirror-sync checks were reported green before this documentation follow-up.
- Final frozen documentation tree: root ran `python3 scripts/run_tests_parallel.py`; the runner reported 4045 tests, 0 failures, 0 errors, and 7 skipped in 130.39 seconds. Log: `.flow/tmp/copilot-high-effort/full-suite-final-docs.log`.
- Follow-up: `./scripts/sync-codex.sh` passed once; `python3 scripts/check_doc_anchors.py` passed; `uvx ruff@0.16.0 check .` passed; content search confirmed the canonical text and generated mirror; `git diff --check` passed.
- All requested local validation is complete; the coordinator owns Flow task state and Git bookkeeping.

### Lifecycle handoff

- Implementation review: `SHIP`, official run `5388114c8c654382b763cc413d9b7cc6`.
- Completion review: `not_required` under the single-task policy because this task's official SHIP review covers the spec surface; no separate completion review ran.
- QA: skipped under policy; this change has no UI path.
- The coordinator owns Flow task state and Git bookkeeping.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: b5d103c1bddec7c114926108c5795ee29adb3799, 97f0cd4a8e4ebc7c3665ff975358d2d0c571b0bc
- Tests: python3 scripts/run_tests_parallel.py at source freeze 97f0cd4a8e4ebc7c3665ff975358d2d0c571b0bc: 4045 tests reported, 0 failures, 0 errors, 7 skipped, python3 scripts/run_tests_parallel.py on final documentation tree: 4045 tests reported, 0 failures, 0 errors, 7 skipped; root run completed in 130.39s, uvx ruff@0.16.0 check .: passed at source freeze and documentation follow-up, ./scripts/sync-codex.sh: passed once for canonical documentation follow-up, python3 scripts/check_doc_anchors.py: passed, git diff --check: passed, full repository suite after documentation freeze: passed; .flow/tmp/copilot-high-effort/full-suite-final-docs.log
- PRs:
