---
title: "Composed brief deleted: path-handoff replaces it (fn-103 eval)"
date: "2026-07-19"
track: knowledge
category: decisions
module: plugins/flow-next/skills/flow-next-work/references/codex-delegation.md
tags: [fn-103, codex-delegation, path-handoff, eval, delegation, bitter-lesson]
applies_when: "considering re-adding per-task composed content to the delegate:codex prompt, or any per-task brief composition for delegated implementation"
decision_status: accepted
alternatives_considered: |
  - composed brief (8-section per-task composition): eval-tied on quality; 5-17 min + ~10x tokens per task
  - path-handoff (chosen): fixed 3-slot template; the task file IS the brief
  - mechanical bundle (inline task+spec bytes): keeps prompt cost; goes stale vs the file
related_to: [knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03]
---

## Decision

The 8-section composed delegation brief in `skills/flow-next-work/references/codex-delegation.md` is DELETED and replaced by a fixed 3-slot path-handoff template (task id, spec id, allowed-file list; "read `.flow/tasks/<id>.md` + `.flow/specs/<id>.md`, implement exactly that task"). The task/spec files ARE the brief - plan-time knowledge reaches executors through the task file, no other channel. The deterministic rails (result schema, classify-result, circuit breaker, scoped rollback, trust cross-check, consent, ralph-guard canonical shape) are byte-preserved: they solve unattended trust with an unobservable external CLI, not model weakness.

Trade-offs: the brief cost 5-17 min of host composition + ~10x prompt tokens per task and added nothing the review layer does not already guarantee at current spec density; the residual risk (thinner tests on code-heavy tasks) closed completely with one general template sentence ("one test per named case - exhaustive, never representative"). Cheaply reversible in prose, but deliberately marked do-not-rebuild (below) so it is not re-grown by habit. Surprise factor: the eval's objective gates TIED on every fixture - the composition layer was pure scaffolding from a weaker-model/thinner-spec era (bitter-lesson framing).

## Eval results (2026-07-19, verbatim)

| Run | Arm | Prompt bytes | Exec secs | Status | Objective gates | F1 test methods |
|---|---|---|---|---|---|---|
| F1A | composed brief (historical, verbatim) | 17518 | 291 | completed | 10/11 | 26 |
| F1B | path-handoff | 1596 | 287 | completed | 10/11 | 11 |
| F1A2 | brief rep2 | 17518 | 321 | completed | 10/11 | 25 |
| F1B2 | path-handoff rep2 | 1596 | 287 | completed | 10/11 | 9 |
| F1B3 | path-handoff + exhaustive-tests sentence | 1652 | 418 | completed | 10/11 | 34 |
| F2A / F2B | brief vs handoff (prose wiring) | 11132 / 1612 | 174 / 209 | completed | 11/11 both | - |
| F3A / F3B | brief vs handoff (prose gates) | 13894 / 1806 | 125 / 183 | completed | 10/10 both | - |

Blind judges (scrambled labels, shipped first-commit diffs as calibration refs) found ZERO Major defects in path-handoff once orchestrator-owned steps (mirror regen, `.flow/bin` dual-copy) were adjudicated as eval artifacts - verified deterministically completable (sync-codex clean on handoff outputs). The F1 single gate failure was identical in every run (spec-interpretation tie, not an arm discriminator). Exec wall-clock within 1.5x both ways. The one stable gradient - test thoroughness on the code fixture (26/25 methods for the brief vs 11/9 for bare handoff) - closed completely with ONE general template sentence (F1B3: 34 methods). The pre-registered DELETE-THE-BRIEF bar was met.

## Alternatives considered

- **Composed brief (status quo):** 8 per-task sections (`<patterns>`, `<approach>`, restated contract, line anchors) composed by the host per task. Rejected: 5-17 min composition + ~10x prompt tokens per task; eval showed zero quality advantage on objective gates or blind judging; the restated contract can drift from the task file it restates.
- **Path-handoff (CHOSEN):** fixed 3-slot template - canonical task/spec file paths, allowed-file list lifted from the task's Files line, unchanged constraints + verify clause (with the eval-validated exhaustive-tests sentence) + output contract. Purely mechanical to assemble; the task file is the single source of truth.
- **Mechanical bundle:** deterministically inline the task+spec file BYTES into the prompt (no judgment, but still duplicated content). Rejected: keeps the prompt-size cost for nothing - the delegate reads files itself; paths are stable while inlined bytes go stale the moment the task file is edited.

## Prevention - do not rebuild without new evidence

Do NOT re-add per-task composed content (patterns/approach/restated-contract sections, line anchors, or any per-task brief composition) to the delegation prompt without a NEW controlled eval that beats path-handoff on objective gates or blind judging. Spec density is the lever when a delegated task underperforms: fix the task file (named files, named test cases, named acceptance - R5 guardrail at the plan skill's task-authoring step + the worker's thin-task valve), not the prompt. The rails are equally protected in the other direction: never cut them for size - they exist for unattended operation, not model coddling.

## Reproduction manifest

- Fixtures: fn-102.1 @ base c92bd7f8, fn-102.2 @ 916f85ed, fn-89.2 @ 586b157e (git worktrees at those SHAs).
- Control prompts: the historical `prompt-batch-1.md` files from `.flow/tmp/codex-<task-id>/` scratch dirs (fn-102.1/.2, fn-89.2) - preserved on the authoring machine; quoted structure in this record's eval section.
- Invocation: `codex exec --ignore-user-config -m gpt-5.6-terra -c model_reasoning_effort="medium" -s workspace-write --skip-git-repo-check --output-schema result-schema.json -o result.json - < prompt.md` (codex-cli 0.144.1).
- Judges: blind subagents, scrambled labels, shipped first-commit diffs as calibration refs.
- Design + full harness scripts: authoring-session scratchpad `/private/tmp/claude-501/-Users-gordon-work-flow-next/f89e09e9-6680-4f29-ba47-66897600d0f7/scratchpad/deleval/` (DESIGN.md, grade_f1.sh, grade_prose.sh, per-run diffs + judge patches). Ephemeral tmp path - the table above is self-contained.
