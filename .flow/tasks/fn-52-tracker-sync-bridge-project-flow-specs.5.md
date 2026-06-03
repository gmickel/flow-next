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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
