---
satisfies: [R1, R2, R3, R4, R7]
---

## Description

Wire the three gate sites to the flowctl `gate` plumbing; every skip loud, per-layer sinks. Prose-only edits; canonical prose stays host-portable ($FLOWCTL fallback chain).

**Size:** M
**Files:** `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, codex mirror (regen)

1. worker.md "Baseline check" (52-63): before running each full gate command from the spec's Quick commands, map it to a (gate_id, exact command) pair and run `$FLOWCTL gate check --gate <id> --command "<cmd>"`; exit 0 -> skip that run, evidence line `GATE_SKIPPED:<gate_id>:green-receipt <sha8> - baseline reused from prior post-gate pass`; else run as today. Lint/format unchanged (always run).
2. worker.md "Verify before completing" (364-371): run `$FLOWCTL gate classify --base $BASE_COMMIT` first; exit 0 -> tier-B (lint/format only - NO suite, NO smoke; mirror regen unaffected because mirror-source diffs never classify tier-B) with `GATE_SKIPPED:unittest:docs-only` + `GATE_SKIPPED:smoke:docs-only` evidence lines; exit nonzero -> full gates as today. After ANY passing full gate run, write its receipt: `$FLOWCTL gate receipt --gate <id> --command "<cmd>"`.
3. worker.md evidence write (383-390): GATE_SKIPPED lines land in `tests[]` (fn-99 plain-string schema); worker summary carries them verbatim.
4. phases.md: Phase 2 (branch setup) persists a SPEC-RUN BASE once - `git merge-base HEAD <base-branch>` at branch creation -> `.flow/tmp/spec_base` (same persistence pattern as worker BASE_COMMIT). Phase 4 "Quality" (475-483): host consults `gate check` per (gate_id, command) before re-running tests, and `gate classify --base $(cat .flow/tmp/spec_base)` for the docs-only tier; honored -> the Phase 5 final summary gains `Gates: baseline reused (green receipt <sha8>)` / `Gates: docs-only tier-B` lines (host sink per R3 - task evidence is closed by then).
5. codex-delegation.md 357-364: `seq 1 6; sleep 10` -> `seq 1 30; sleep 2` (same 60s bound, ~5x less overshoot); sweep worker.md/phases.md for other fixed full-interval sleeps, same treatment. No orphaned background sleeps (group-kill lesson, memory bash-deadline-watchdogs-orphaned-sleep-2026-07-16).
6. Cross-platform checklist: sync-codex.sh x2 idempotent, guards green, mirror committed with canonical change; gate calls are plain bash + $FLOWCTL (portable to Cursor/Droid as-is; Codex mirror rewrite untouched).

## Acceptance
- [ ] R1: both worker gate sites + host Phase 4 honor receipts with command fingerprints; receipts written after every passing full gate
- [ ] R2: classification consulted live at each gate decision (worker Verify via BASE_COMMIT; host via spec_base)
- [ ] R3: worker skips -> task tests[]; host skips -> Phase 5 summary lines; zero silent skips
- [ ] R4: no fixed full-interval sleeps remain in the three files' poll paths
- [ ] R7: mirror regen x2 idempotent, guards green

## Done summary
Wired the fn-102 gate diet into the work-loop prose: worker Baseline check honors green receipts via `gate check` per (gate_id, command) with loud GATE_SKIPPED evidence, Verify-before-completing runs `gate classify` for docs-only tier-B (lint/format only, human-claused skip lines) and writes receipts after passing full gates, host phases.md persists a spec-run base (`.flow/tmp/spec_base`) and consults check/classify at Phase 4 with per-outcome `Gates:` lines in the Phase 5 summary, and the codex-delegation poll loop moved from 10s to 2s intervals (same 60s bound). Implementation delegated to codex gpt-5.6-terra (medium); codex mirror regenerated x2 idempotent; codex impl-review r1 NEEDS_WORK (Gates-slot accumulation + missing human clause) fixed -> r2 SHIP.
## Evidence
- Commits: 168c096e0e5e7095b65194dcffda97adc73a1249, 28f5c0bb6828d12d5532ddd4c264243ceaa29ba9
- Tests: baseline: green (python3 -m unittest discover -s plugins/flow-next/tests -q pre-edit run passed; corroborated by fn-102.1 post-gate 1818 OK on the same tree - delta was a .flow-only chore commit), python3 -m unittest discover -s plugins/flow-next/tests -q (exit=0, full suite green at 168c096e post-delegation tree), python3 -m unittest -q test_worker_anchor_prose test_ralph_guard_codex_delegation test_codex_delegation_classify test_codex_delegation_gates test_gate_receipt test_gate_classify test_cp1252_robustness (206 tests OK at branch tip 28f5c0bb), python3 -m unittest -q test_anchor_bundle test_work_delegate_config (40 tests OK at branch tip - completes coverage of every module reading the edited files), ./scripts/sync-codex.sh x2 (idempotent, zero second-run diff, guards green - run twice again after r1 fixes)
- PRs: