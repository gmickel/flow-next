# Per-run claim identity for same-actor session contention

## Goal & Context

flowctl identifies claim owners by git email. Two concurrent runs by the same person (second terminal, scheduled pilot tick, second machine on a shared checkout) share that actor, and `flowctl start` treats an `in_progress` task with the same assignee as a RESUME - so the second run can silently steal a task the first run is mid-flight on, and both dispatch workers for it. Cross-actor contention already fails closed; same-actor contention does not. Surfaced by codex review on PR #365 (fn-203 rolling beta), but the semantics are canonical `/flow-next:work`'s too - any cross-session parallelism has the hole. Structural containment exists today (isolated worktrees make the collision surface as an integration conflict + serial retry, never silent corruption), so this is a duplicate-work/liveness defect, not a correctness one.

## Tracker issues this resolves

- **#369** (refusal seam before `flowctl start` writes a claim) and **#370** (Worktree Kit `create` should surface the resolved actor) both describe the same collision from the consumer side: two runners on one machine resolve to one git email and the second silently resumes the first's claim. This spec removes the collision itself, so both stay parked on it (maintainer replies 2026-08-27). After it ships, re-read both: a config leaf in `cmd_start` rejecting placeholder actors such as `unknown` is the only shape from #369 still worth considering, and the #370 print-out is judged against the post-token behaviour, never built as a Kit-written `FLOW_ACTOR`.
- Not to be confused with #368 (land ledger locality), closed 2026-09-13.

## Refresh before planning (2026-09-13)

The references above predate 5.x. Re-anchor before planning:

- "fn-203 rolling beta" and "work-rolling prose" are gone; rolling is work's default since fn-218 and the scheduler prose lives in `skills/flow-next-work/references/rolling-scheduler.md`, which already mints a `RUN_ID` (timestamp plus pid) for the notes directory. The `.flow/tmp/notes_dir` pointer is still one shared path per checkout, so the second in-scope item stands.
- The claim surfaces are now `skills/flow-next-work/phases.md` (3b claim, direct-owner resume admission), `references/no-plan-route.md` (which states outright that same-actor `flowctl start` cannot tell two runs apart), `skills/flow-next-flow/auto.md` (resume consent and stale-claim rows), and `references/backlog-mode.md` 1g. Flow `--auto` already gates an own-claim resume on positive evidence that the prior run ended; the token should replace that prose proof, and R2 is reworded against these files.
- The token is minted at flow run start (not "Phase 2 / scheduler start") so it carries across hops. `cmd_start` already has `--reclaim`; the explicit resume path reuses it rather than adding `--resume`/`--force`.

## Proposed shape (to be planned)

- Give each run a distinct claim identity: actor + run-id (e.g. a per-run token minted at Phase 2 / scheduler start, persisted like `.flow/tmp/spec_base`), carried on claims.
- Preserve legitimate resume: an explicit resume path (same run-id, or an explicit `--resume`/`--force`) keeps the crash-recovery ergonomics; a DIFFERENT run-id with the same actor refuses like a foreign claim.
- Audit both work skills' claim/contention prose against the new semantics (the fn-203 beta's foreign-in-flight checks generalize cleanly: "foreign" becomes "not this run-id" rather than "not this actor").

- Also in scope (same concurrent-same-actor class, surfaced by codex r6 on PR #365): the rolling beta's `.flow/tmp/notes_dir` pointer is a single shared path, so two concurrent runs on one checkout cross-wire notes surfaces (second run overwrites the pointer; first run's cleanup can delete the second's active dir). Key the pointer by the same per-run identity this spec introduces.

## Acceptance Criteria

- R1: A second same-actor run's `flowctl start` on an in_progress task refuses (typed contention) unless an explicit resume path is taken; crash-recovery resume still works; focused deterministic tests cover both.
- R2: Canonical work and work-rolling prose updated to the run-identity semantics; sync-codex idempotent; docs note the change.
