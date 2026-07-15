# fn-99-setup-block-diet-evidence-schema-inline.2 Guidance-eval harness: commit under agent_docs, extend with multi-task scenario, baseline

## Description
Commit the clean-room guidance-eval harness and record the attributable baseline. Satisfies R4 (harness half), R13. Depends on .1 (baseline must run against the FINAL dieted block: named "post-block-diet, pre-usage-trim" - running against the old 575-token block would confound task .4's attribution).

Scope:
1. New `agent_docs/guidance-eval/`: runner script (scaffolds scratch repos under its own tmp; arms = guidance variants; models via bridge CLIs), scenario prompt files, deterministic grader (.flow state + flowctl logging shim: spec/task created, done-with-valid-evidence, no markdown TODOs, tests green, invocation/error counts), README with grading contract + results ledger (optimization-log table style) + documented threat model.
2. Clean-room + hardening requirements (binding): `claude -p --bare` (else ~/.claude leaks in - observed); explicit `--permission-mode acceptEdits --allowedTools`; codex via `--sandbox danger-full-access --skip-git-repo-check` (workspace-write blocks git commit in scratch dirs - observed confound) WITH: per-run timeout + process-tree termination, unique run ids, cwd + nested-git-root preflight before any bridge call, retained stdout/stderr/grade artifacts per run, failed/incomplete summary at batch end. Foreground bridge calls only. Container/VM deliberately not required (spec Decision Context - documented exposure in README).
3. Scenarios: (a) round-1 single-task slugify; (b) NEW multi-task: spec with 2-3 tasks + one dependency + one reset-or-block lifecycle event.
4. Baseline matrix (R13, recorded in the ledger with model ids + date): scenarios (a,b) x arms (minimal-block, full-block) x models (sonnet, terra-medium, haiku) x reps (3 on discriminating cells, 1 elsewhere). Baseline = post-block-diet, pre-usage-trim.

Port shapes from the session harness described in memory `usage-md-guidance-eval-2026-07-15` (recreate; scratchpad is session-local).
## Acceptance
- agent_docs/guidance-eval/ committed and runnable end-to-end by a fresh contributor with claude/codex CLIs; README documents grading contract, ledger, exposure.
- Runner: --bare, explicit permissions, hardening set (timeouts, kill-tree, preflights, run ids, artifacts, batch summary), foreground only.
- Both scenarios graded deterministically; multi-task covers dep + reset/block.
- Baseline ledger rows recorded post-block-diet/pre-usage-trim with the full R13 matrix incl. haiku floor.
- No CI wiring; no shipped-plugin file changes.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
