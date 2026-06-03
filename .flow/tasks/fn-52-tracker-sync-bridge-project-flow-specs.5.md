---
satisfies: [R7, R8]
---

## Description

Status/metadata reconciliation (who-wins) + comments/evidence two-way append, behind the .2 orchestration and .3 transport. Independent of the body merge (.4) — runs in parallel; different reference files.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md`, `references/comments-sync.md`.

## Approach

- **Status who-wins (R7):** per-field policy table (NOT one global rule). Tracker wins terminal states (`done`/`verified`/closed); flow wins `in-progress`/early; priority + `deferred`/`wontfix` **surface to the user, never auto-changed**. Map Linear `workflowState.type` (`triage|backlog|unstarted|started|completed|canceled`) ↔ flow status, with an explicit fallback for an unmapped custom state (no crash, warn). **Status deadlock** (tracker `done` + flow `in-progress` simultaneously) → fall back to the R1 `conflictTiebreak` default; under `always-ask` in autonomous mode → queue.
- **Comments/evidence append (R8):** flow lifecycle events post structured comments to the issue; tracker comments pull into the spec's sync log; append-only (no conflict). **Dedup:** embed a hidden marker `<!-- flow-next:sync evidence=<sha> spec=<id> -->` + store the posted comment id + match on a **normalized-text** hash (avoid whitespace false-new). A human-pasted copy of a flow comment must not be re-posted. **Append-only is the default (R8).** The one edit-in-place exception is a single flow-owned "flow-next status" rolling comment (clearly marked, opt-in) updated via its marker — this is the SOLE edit-in-place surface and does not apply to evidence/lifecycle/user comments, which stay strictly append-only. If the rolling comment adds complexity, drop it and append; do not weaken the append-only contract for any other comment.

## Investigation targets

**Required:**
- the .1 sync receipt + `conflictTiebreak` config + deferred sink
- the .2 orchestration + adapter interface (`readStatus`/`setStatus`/`listComments`/`postComment`)
- the .3 Linear transport (workflowStates, commentCreate)

**Optional:**
- Linear/GitHub comment + state docs (status model, comment ids)

## Acceptance

- [ ] Status reconciled two-way with per-field who-wins: tracker wins terminal, flow wins in-progress, priority/`deferred`/`wontfix` surfaced not auto-changed [R7]
- [ ] Status deadlock falls back to the R1 `conflictTiebreak` default (and queues under `always-ask` in autonomous mode) [R7]
- [ ] Linear `workflowState.type` ↔ flow status mapping documented with an unmapped-state fallback (no crash) [R7]
- [ ] Comments/evidence two-way append; dedup via embedded marker + normalized hash + comment id — re-sync posts no duplicates; a human-pasted flow comment is not re-posted [R8]

## Done summary
Implemented status/metadata who-wins (R7) and comments/evidence two-way append (R8) for the flow-next-tracker-sync skill as two new reference files: references/status-sync.md (per-field who-wins — tracker wins terminal, flow wins in-progress, priority/deferred/wontfix surfaced never auto-changed; status deadlock evaluated FIRST and routed to the R1 conflictTiebreak, queuing under always-ask in Ralph; Linear state.type ↔ flow status map with a warn+surface unmapped-state fallback; six worked fixtures S-A..S-F) and references/comments-sync.md (append-only two-way comments/evidence with three-layer dedup — embedded marker, stored posted-id, normalized-text hash that catches a human paste; lifecycle event→comment map; sync-log fold that never promotes to an R-ID; a single opt-in rolling status comment as the sole edit-in-place exception; five fixtures C-A..C-E). Wired the now-implemented reconcile hooks into SKILL.md/steps.md/adapter-interface.md/linear-ladder.md (no lingering fn-52.5 stubs). Strictly-live setStatus/postComment round-trips are deferred to the post-PR smoke phase per the established pattern; all policy/dedup/mapping logic is runnable without a live tracker. impl-review (rp): NEEDS_WORK → SHIP after fixing a deadlock-ordering bug (terminal-wins fired before the deadlock fallback).
## Evidence
- Commits: 0140f67, 6488231, fd49b3c
- Tests: bash plugins/flow-next/scripts/ci_test.sh (58 passed / 0 failed), cross-ref link resolution on status-sync.md + comments-sync.md (0 broken), markdown fence-balance check (both balanced), flowctl validate --spec fn-52 (valid: true), impl-review rp backend: NEEDS_WORK (1 Major, conf 100) -> fixed -> SHIP (0 introduced findings; R7 + R8 covered)
- PRs: