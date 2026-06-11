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
resolve-pr gains the fn-59.2 autonomous mode: Phase 0 parses + strips the `mode:autonomous` token (make-pr parse shape) with `FLOW_AUTONOMOUS=1` as secondary signal, the Phase 10 needs-human surface emits `NEEDS_HUMAN:` report lines plus the machine-readable `RESOLVE_PR_VERDICT=` terminal line under autonomy (interactive path byte-identical, never Ralph/receipt paths), and the Forbidden line carries the confined /flow-next:land dispatch exception. flowctl seeds the land.* config defaults (release=true, patienceMinutes=30, reviewSignal=silence, automatedReviewers="", ciFixBudget=3) with a new stdlib test file; dogfood flowctl.py copy refreshed to keep the dual-copy invariant green. Codex impl-review: SHIP (first pass).
## Evidence
- Commits: 72c63d256a4c935de37624c9a7a2c72c048edd2e
- Tests: python3 plugins/flow-next/tests/test_land_config.py (13 tests OK), for f in plugins/flow-next/tests/test_*.py; do python3 $f; done (full suite green), .flow/bin/flowctl config get land.reviewSignal --json -> silence, bash -n scripts/sync-codex.sh && ./scripts/sync-codex.sh (validators green; mirror diff reverted, regen rides fn-60.3)
- PRs: