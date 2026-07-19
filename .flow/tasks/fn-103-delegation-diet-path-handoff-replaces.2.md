---
satisfies: [R4, R5, R6, R7]
---

## Description

Docs reframe, the plan-side density sentence, the decision record, CHANGELOG.

**Size:** S
**Files:** `plugins/flow-next/docs/orchestration.md`, `plugins/flow-next/docs/README.md` (codex-delegation row - batching vocabulary), `plugins/flow-next/skills/flow-next-setup/templates/usage.md` (the CANONICAL source - never edit .flow/usage.md directly), `plugins/flow-next/skills/flow-next-plan/steps.md`, `.flow/memory/knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19.md` (new), `CHANGELOG.md`, codex mirror (regen)

1. orchestration.md: reframe the delegation section - the RAW codex-exec bridge is the interactive route; `delegate:codex` = the same bridge with deterministic rails for unattended loops; prompt = fixed path-handoff template (task/spec files ARE the brief). Light touch - the existing host-retains-judgment framing (L59-71) survives.
2. setup templates/usage.md § Orchestration: same reframe in the "flow-next shortcuts" block; verify the bridge recipes need no change (they are already raw-bridge-first).
3. plan steps.md (~L445-485 task template): ONE sentence - task files must carry the full contract (named files, named test cases, named acceptance) because downstream executors receive the task file AS the brief.
4. Decision record per docs/memory-schema.md frontmatter (title, date, track: knowledge, category: decisions, module: skills/flow-next-work/references/codex-delegation.md, tags, applies_when) + alternatives considered (composed brief / path-handoff / mechanical bundle) + the FULL eval results table (embedded below - self-contained, no session dependency) + do-not-rebuild-without-new-evidence prevention clause + reproduction manifest.

**Eval results (2026-07-19, embed verbatim in the record):**

| Run | Arm | Prompt bytes | Exec secs | Status | Objective gates | F1 test methods |
|---|---|---|---|---|---|---|
| F1A | composed brief (historical, verbatim) | 17518 | 291 | completed | 10/11 | 26 |
| F1B | path-handoff | 1596 | 287 | completed | 10/11 | 11 |
| F1A2 | brief rep2 | 17518 | 321 | completed | 10/11 | 25 |
| F1B2 | path-handoff rep2 | 1596 | 287 | completed | 10/11 | 9 |
| F1B3 | path-handoff + exhaustive-tests sentence | 1652 | 418 | completed | 10/11 | 34 |
| F2A / F2B | brief vs handoff (prose wiring) | 11132 / 1612 | 174 / 209 | completed | 11/11 both | - |
| F3A / F3B | brief vs handoff (prose gates) | 13894 / 1806 | 125 / 183 | completed | 10/10 both | - |

Reproduction manifest: fixtures = fn-102.1 @ base c92bd7f8, fn-102.2 @ 916f85ed, fn-89.2 @ 586b157e (git worktrees at those SHAs); control prompts = the historical `prompt-batch-1.md` files from `.flow/tmp/codex-<task-id>/` scratch dirs (fn-102.1/.2, fn-89.2 - preserved on the authoring machine + quoted structure in the record); invocation = `codex exec --ignore-user-config -m gpt-5.6-terra -c model_reasoning_effort="medium" -s workspace-write --skip-git-repo-check --output-schema result-schema.json -o result.json - < prompt.md` (codex-cli 0.144.1); judges = blind subagents, scrambled labels, shipped first-commit diffs as calibration refs; F1 single gate failure identical in every run (spec-interpretation tie, not an arm discriminator); Majors adjudicated as eval artifacts were the orchestrator-owned mirror/dual-copy steps, verified deterministically completable (sync-codex clean on handoff outputs). Design + full harness scripts: authoring-session scratchpad `deleval/` (absolute path in the record).
5. CHANGELOG `## Unreleased` entry (batched, no bump.sh).
6. **Repo-wide final sweep gate:** `grep -rn 'per-batch\|units were trivial' plugins/flow-next --include='*.md'` returns ZERO hits outside historical CHANGELOG entries and .flow/memory (flowctl.py exempt - zero code changes; docs/README.md L44 row updated here). Record the grep output in evidence.
7. **Downstream handoff (named, separate repo):** the flow-next.dev orchestration page mirrors the delegate:codex passages - the same interactive-raw-bridge vs unattended-rails reframe is applied in ~/work/flow-next.dev in the landing workstream (not this repo's diff); record the handoff in the done summary so the lander walks it.
8. sync-codex x2 idempotent, guards green (docs are not mirrored; the steps.md edit IS - verify).

## Acceptance
- [ ] R4: both doc surfaces reframed; no composed-brief prescription anywhere
- [ ] R5 (plan side): density sentence in the task-authoring step
- [ ] R6: decision record schema-compliant with alternatives + eval table + prevention clause
- [ ] R7: mirror idempotent, guards green; no version bump

## Done summary
Docs reframe + plan-density sentence + decision record + CHANGELOG for the delegation diet (fn-103). orchestration.md and the setup usage.md template (plus dogfooded .flow/usage.md) now present the raw codex exec bridge as the interactive route and delegate:codex as the same bridge with deterministic rails for unattended loops (fixed path-handoff prompt; task/spec files ARE the brief); docs/README.md delegation row swaps batching for one-run-per-task; plan steps.md task template carries the R5 density sentence; R6 decision record with alternatives, verbatim eval table, do-not-rebuild clause and reproduction manifest landed at .flow/memory/knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19.md; CHANGELOG Unreleased entry added (no version bump). Sweep gate green (grep zero hits), mirror regenerated x2 idempotent, full suite green, codex impl-review SHIP (r1: dual-copy usage.md parity fix). Implementation delegated to codex gpt-5.6-terra@medium via the NEW path-handoff template (first production use) - partial (orchestrator-owned steps excluded by scope), finished locally. DOWNSTREAM HANDOFF (for the lander): apply the same interactive-raw-bridge vs unattended-rails reframe to the flow-next.dev orchestration page in ~/work/flow-next.dev (separate repo, landing workstream - not in this diff).
## Evidence
- Commits: 4333eb68dab0f3ad6d17e21ab0c7b46b5af20602, 1685a438743f78d038d32f56a48733190add6848
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (baseline: green pre-edit; post-edit: 1838 tests OK, green receipt 1685a438-unittest), python3 -m unittest plugins.flow-next.tests.test_dogfood_template_parity (r1 fix verification), grep -rn per-batch|units were trivial plugins/flow-next --include=*.md -> zero hits (R4 sweep gate), ./scripts/sync-codex.sh x2 idempotent, guards green
- PRs: