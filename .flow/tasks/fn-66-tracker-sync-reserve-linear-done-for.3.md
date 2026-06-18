# fn-66-tracker-sync-reserve-linear-done-for.3 Pilot all-done hardening: never NO_WORK for an all-done spec lacking a merged PR

## Description
### Goal
Harden pilot so an all-done / completion-ship spec lacking a merged PR can never silently reach terminal `NO_WORK`. Satisfies R5, R6.

### Investigation targets
- `flow-next-pilot/workflow.md:109-141` — Phase 2 CLASSIFY, all-done branch (`:118`) + PR probe (`:135-141`). Current outcomes: OPEN PR → skip to next candidate (`:138`); no PR → `make-pr` (`:141`); MERGED + open-spec → NEEDS_HUMAN (`:140`); CLOSED-unmerged → NEEDS_HUMAN (`:139`).
- **The gap**: SELECT (`:64-91`) only picks `status=="open"` specs. An all-done spec with an OPEN PR is skipped (`:138`, land owns it) — correct — BUT if it's the sole candidate the loop falls to `NO_WORK` (`:90`). Harden: the open-PR skip must be explicit "defer to land" (a distinct reason), and an all-done spec with NO open AND NO merged PR must ALWAYS route to `make-pr` (never NO_WORK). Closed-unmerged / missing-branch / merged-but-open-spec stay `NEEDS_HUMAN` (R6).
- The PR probe shape is already `:126-132` (OPEN/CLOSED/MERGED). Reuse — this is classification hardening + reason clarity, not new probing.
- Crash-class note `:304` may need the new case.

### Notes
Independent of fn-66.1/.2 (edits only pilot workflow.md), but conceptually the pilot-side of the same "all-done ≠ shipped" invariant. Pilot is host-agent skill prose — no flowctl change; covered by the status-sync worked-fixture style, not a unit test (state honestly).
## Acceptance
- [ ] An all-done / completion-ship spec with NO open and NO merged PR classifies as `make-pr`, never terminal `NO_WORK` (R5).
- [ ] An all-done spec with an OPEN PR is deferred to land with an explicit distinct reason (not a silent NO_WORK).
- [ ] Closed-unmerged PR, missing branch, or merged-but-still-open-spec → `NEEDS_HUMAN` (R6), never Done/NO_WORK.
- [ ] The classification table + crash-class note in pilot workflow.md reflect the new cases; reasons are greppable in the verdict line.
## Done summary
Hardened pilot's all-done classification: an all-done spec with an open PR now emits an explicit greppable PILOT_VERDICT=DEFERRED_TO_LAND (stage=land) instead of silently collapsing to terminal NO_WORK; no-PR all-done always classifies make-pr (FLOW-15 case); closed-unmerged/missing-branch/merged-but-open-spec stay NEEDS_HUMAN. Registered the new DEFERRED_TO_LAND verdict token + land stage in the SKILL.md grammar and ralph.md /goal driver recipes; regenerated the Codex mirror.
## Evidence
- Commits: 17e58dccc80b9ae73955a7381c3fa18e8e1b5da9, 6f69001c95676ad9ac3bd985a6216131ad28e69b
- Tests: bash plugins/flow-next/scripts/ci_test.sh (67 passed, 0 failed), bash scripts/sync-codex.sh (mirror regen, all gates pass)
- PRs: