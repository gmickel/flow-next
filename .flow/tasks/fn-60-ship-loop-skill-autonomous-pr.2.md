---
satisfies: [R4, R5, R15]
---

## Description

Two thin patches: (1) resolve-pr gains the fn-59.2 autonomous mode — `mode:autonomous` token primary + `FLOW_AUTONOMOUS=1` secondary, question-suppression only — plus the confined Forbidden carve-out for land's dispatch; (2) flowctl seeds the `land.*` config defaults.

**Size:** M
**Files:** plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md, plugins/flow-next/skills/flow-next-resolve-pr/workflow.md, plugins/flow-next/scripts/flowctl.py, plugins/flow-next/tests/ (one test file), .flow/bin parity n/a (dogfood copy refreshed at release)

## Approach

- resolve-pr workflow.md Phase 0 (:23-30): parse + strip `mode:autonomous` using make-pr's bash parse shape (`flow-next-make-pr/SKILL.md:44-65`); derive `AUTONOMOUS=1` also from `FLOW_AUTONOMOUS=1`.
- workflow.md:420 (Phase 10 needs-human surface): under `AUTONOMOUS=1`, do NOT AskUserQuestion — emit per-thread `NEEDS_HUMAN: <thread> — <reason>` report lines, leave threads open, and end the run with the machine-readable terminal line `RESOLVE_PR_VERDICT=<RESOLVED|PENDING|NEEDS_HUMAN> threads=<n> fixed=<n> needs_human=<n>` (last line, nothing after — land gates on it). Demotion/skip logic (:286,293,318,337) untouched. Bounded 2 fix-verify cycles unchanged; cycle-3 escalation under autonomy = NEEDS_HUMAN report.
- SKILL.md:88 Forbidden line: append the confined exception — `/flow-next:land` may dispatch resolve-pr with `mode:autonomous` (autonomy ≠ Ralph; no receipt paths). Mirror the "Autonomy ≠ Ralph" sentence from work SKILL.md:62.
- flowctl.py config defaults (~:1129, mirror `work.delegate*` block): seed `land.release=true`, `land.patienceMinutes=30`, `land.reviewSignal="silence"`, `land.automatedReviewers=""`, `land.ciFixBudget=3`. Add a stdlib test (tests/test_*.py pattern) asserting `config get land.*` returns seeded values on a fresh repo and `config set` round-trips.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md:23-30,280-360,415-430` — parse + needs-human surfaces
- `plugins/flow-next/skills/flow-next-make-pr/SKILL.md:44-78` — the parse-loop shape + flag-table row precedent
- `plugins/flow-next/scripts/flowctl.py:1125-1170` — config defaults + alias registry
- `plugins/flow-next/tests/test_work_delegate_config.py` — test pattern to mirror

**Optional:**
- `plugins/flow-next/skills/flow-next-work/SKILL.md:55-63` — Autonomous Mode prose template

## Acceptance

- [ ] resolve-pr parses + strips `mode:autonomous` (token) and honors `FLOW_AUTONOMOUS=1` (env), question-suppression branches only — never sets RALPH, never touches receipt paths
- [ ] Phase-10 needs-human under autonomy reports `NEEDS_HUMAN` lines instead of AskUserQuestion; threads stay open; interactive behavior byte-identical
- [ ] Autonomous runs end with the terminal `RESOLVE_PR_VERDICT=…` line exactly per spec (absent in interactive mode)
- [ ] Forbidden line carries the confined land exception (one sentence, no new section)
- [ ] `land.*` defaults seeded; `flowctl config get land.reviewSignal --json` → "silence" on fresh repo; test green
- [ ] All existing tests pass; sync-codex validators green (mirror diff reverted; regen rides fn-60.3)

## Done summary
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: resolve-pr autonomous handling and land.* seeded defaults shipped with land 1.14.0. No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs: