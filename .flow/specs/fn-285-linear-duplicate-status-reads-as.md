# Linear Duplicate status reads as cancelled

## Goal & Context

GitHub issue #522 (reported by @sn-furali). Marking a Linear issue as a duplicate moves it into Linear's system-managed Duplicate status (`WorkflowState.type` `duplicate`, documented by Linear as its own category and not renameable). flowctl's Linear status read falls back to the state type when no `stateIds` mapping matches, and that fallback covers `triage`, `backlog`, `unstarted`, `started`, `completed` and `canceled` but not `duplicate`, so every status normalization of a duplicated issue fails with `CONFLICT` / `unmapped-state`. A duplicate is a terminal, not-done outcome, so it should read as `cancelled`.

## Acceptance Criteria

- **R1:** A linked Linear issue in a state of type `duplicate` (no `stateIds` mapping for that state) normalizes to `cancelled` instead of returning `unmapped-state`. No error surface beyond the existing `unmapped-state` for types still unknown.

## Boundaries

- The write side is unchanged: Linear state resolution does not add the Duplicate state to any slot pool, so a cancel that flow-next writes keeps targeting the configured cancelled state and never moves an issue into Duplicate.
- No new query fields (`canceledAt` / `completedAt`).

## Decision Context

The reporter offered two fixes: honour `canceledAt` / `completedAt` before giving up, or map `duplicate` to `cancelled` in the read taxonomy. The taxonomy entry is the smallest correct change; the timestamp route needs a query change and covers only hypothetical future terminal types. Adding `duplicate` to the write pools would let state resolution pick Duplicate for the cancelled slot, which is the misbehaviour the report warns about.
