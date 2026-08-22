# Per-run claim identity for same-actor session contention

## Goal & Context

flowctl identifies claim owners by git email. Two concurrent runs by the same person (second terminal, scheduled pilot tick, second machine on a shared checkout) share that actor, and `flowctl start` treats an `in_progress` task with the same assignee as a RESUME - so the second run can silently steal a task the first run is mid-flight on, and both dispatch workers for it. Cross-actor contention already fails closed; same-actor contention does not. Surfaced by codex review on PR #365 (fn-203 rolling beta), but the semantics are canonical `/flow-next:work`'s too - any cross-session parallelism has the hole. Structural containment exists today (isolated worktrees make the collision surface as an integration conflict + serial retry, never silent corruption), so this is a duplicate-work/liveness defect, not a correctness one.

## Proposed shape (to be planned)

- Give each run a distinct claim identity: actor + run-id (e.g. a per-run token minted at Phase 2 / scheduler start, persisted like `.flow/tmp/spec_base`), carried on claims.
- Preserve legitimate resume: an explicit resume path (same run-id, or an explicit `--resume`/`--force`) keeps the crash-recovery ergonomics; a DIFFERENT run-id with the same actor refuses like a foreign claim.
- Audit both work skills' claim/contention prose against the new semantics (the fn-203 beta's foreign-in-flight checks generalize cleanly: "foreign" becomes "not this run-id" rather than "not this actor").

## Acceptance Criteria

- R1: A second same-actor run's `flowctl start` on an in_progress task refuses (typed contention) unless an explicit resume path is taken; crash-recovery resume still works; focused deterministic tests cover both.
- R2: Canonical work and work-rolling prose updated to the run-identity semantics; sync-codex idempotent; docs note the change.
