---
satisfies: [R1, R2, R3, R4, R7]
---

## Description

Wire the three gate sites to the new flowctl `gate` plumbing and make every skip loud. Prose-only edits to the work loop; canonical prose stays host-portable ($FLOWCTL fallback chain, no Claude-only constructs).

**Size:** M
**Files:** `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, `scripts/sync-codex.sh` (regen only unless a guard is needed), codex mirror

1. worker.md "Baseline check" (52-63): before running each full gate (unittest, smoke), run `$FLOWCTL gate check --gate <id>`; exit 0 -> skip that gate's run and record the evidence line `GATE_SKIPPED:<gate_id>:green-receipt <sha8> - baseline reused from prior post-gate pass`; exit nonzero -> run exactly as today. Lint/format unchanged (always run).
2. worker.md "Verify before completing" (364-371): first run `$FLOWCTL gate classify --base $BASE_COMMIT`; exit 0 -> tier-B gate set (sync-codex x2 + guards IFF the diff touches `plugins/flow-next/{skills,agents,commands,references}/**`, else skip mirror step; lint per repo) and evidence line `GATE_SKIPPED:unittest:docs-only ...` + `GATE_SKIPPED:smoke:docs-only ...`; exit nonzero -> full gates as today. After ANY full gate passes, write its receipt: `$FLOWCTL gate receipt --gate <id>`.
3. worker.md evidence write (383-390): the GATE_SKIPPED lines land in `tests[]` (fn-99 schema: plain strings - compatible). Worker summary carries them verbatim.
4. phases.md Phase 4 "Quality" (475-483): host consults `gate check` per gate before re-running tests; honored -> state "baseline reused (green receipt <sha8>)" in the run log instead of re-running; classification honored the same way for docs-only spec diffs. Phase 5 summary template unchanged.
5. codex-delegation.md 357-364: poll loop `seq 1 6; sleep 10` -> poll every 2s bounded at the same 60s total (`seq 1 30; sleep 2`), same result-file probe. Watch the group-kill lesson (no orphaned background sleeps; memory bash-deadline-watchdogs-orphaned-sleep-2026-07-16). Sweep worker.md/phases.md for other fixed full-interval sleeps; same treatment.
6. Cross-platform checklist: sync-codex.sh x2 idempotent, guards green, mirror committed with canonical change; no new Claude-only phrases (plain `$FLOWCTL` invocations rewrite cleanly); Cursor/Droid consume canonical as-is - the gate calls are bash, portable.

## Acceptance
- [ ] R1: both worker gate sites + host Phase 4 honor receipts; receipts written after every passing full gate
- [ ] R2: classification consulted at the Verify site over the cumulative live diff (never cached from task start)
- [ ] R3: GATE_SKIPPED evidence lines + summary lines on every skip; zero silent skips
- [ ] R4: no fixed full-interval sleeps remain in worker.md/phases.md/codex-delegation.md poll paths
- [ ] R7: mirror regenerated x2 idempotent, guards green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
