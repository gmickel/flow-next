---
satisfies: [R2, R5]
---

## Description

Wire the end-of-run sync check + one-cycle retro-fire + mandatory summary slot into the work skill, and have its three touchpoints pass `--event` through to the tracker-sync skill.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/phases.md`

## Approach

- Three touchpoints pass their event into the tracker-sync invocation: 3b.1 firstClaim (:205-222), 3d.1 done (:290-307), 3g completionReview (:413-427) — events `work.firstClaim`, `work.done`, `work.completionReview`.
- **Phase 5 Ship (:465-484)** gains the check as the LAST substantive action before the summary (recency = stickiness): one concrete copy-pasteable bash block — derive `--since` from the earliest `claimed_at` among tasks worked this run (`flowctl show` per task; on-disk anchor since bash vars do not survive across tool calls); derive `--events` from what occurred (≥1 claim → firstClaim; ≥1 done → done; completion-review ran → completionReview); run `"$FLOWCTL" sync check "$SPEC_ID" --events "$EVENTS" --since "$SINCE" --json`.
- On MISSING: retro-fire by invoking the tracker-sync skill ONCE for the missed event (never the check wrapper — no recursion), re-check with `--since` = retro-fire start, record final state.
- **Mandatory summary slot** in the Phase 5 output template (this is the forcing function — a template field, not a checklist bullet): `Tracker sync: OK | MISSING:<event> → retro-fired → OK | MISSING:<event> (retro-fire failed: <reason>) | n/a (bridge inactive)`. The `n/a` state is explicit — an absent field must be distinguishable from an inactive bridge.
- Under Ralph: check output + summary line to **stderr** / the summary block — work's stdout stays clean for harness parsing.
- Update the example-flow diagram (:496-508) and "Definition of Done" (:486-494) to include the tracker-sync slot.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-work/phases.md:205-222, 290-307, 413-427` — the three touchpoint blocks
- `plugins/flow-next/skills/flow-next-work/phases.md:465-508` — Phase 5 Ship + Definition of Done + example flow
- `.flow/specs/fn-57-tracker-sync-lifecycle-hooks-forcing.md` §Check semantics — the exact predicate/vocabulary to embed

**Optional:**
- `plugins/flow-next/skills/flow-next-work/SKILL.md:33-38, 139` — Ralph rules + touchpoint table (update the table if it lists events)

## Acceptance

- [ ] All three touchpoints pass `event:` to the tracker-sync skill invocation
- [ ] Phase 5 contains the concrete check block (exact flags, on-disk `--since` derivation, triggered-set rules) as the last action before the summary
- [ ] The summary template carries the mandatory four-state `Tracker sync:` slot; bridge-inactive renders explicit `n/a`
- [ ] Retro-fire is bounded to one cycle, dispatches tracker-sync directly, and a still-MISSING outcome is recorded + visible, never blocking
- [ ] Ralph mode: no new stdout pollution (check/summary routed per existing conventions)

## Done summary
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: work skill's end-of-run tracker-sync check (perEvent gating) is in the shipped skill. No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs: