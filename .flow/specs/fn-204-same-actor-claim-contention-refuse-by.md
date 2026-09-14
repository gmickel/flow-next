# Same-actor claim contention: refuse by default, resume by explicit reclaim

**Rewritten 2026-09-14.** The August draft proposed a per-run identity token carried on every claim. That is more identity machinery than the hole needs and the first step toward runner coordination this project does not want. This version closes the same hole with one behaviour flip on a verb that already exists.

## Goal & Context
<!-- scope: business -->

flowctl identifies a task's claimant by git email. A task that is `in_progress` under a different email refuses a second `flowctl start` (foreign claim, fail closed). A task that is `in_progress` under your own email is handed back as a resume. That is what makes crash recovery work, and it is also the hole: two runs by the same person on one clone (a second terminal, a scheduled `flow --auto` tick, a second machine on a shared checkout) share the email, so the second run's `start` reads as a resume and dispatches a second worker onto a task the first run is mid-flight on. Nothing errors. Surfaced by codex review on PR #365; issues #369 and #370 describe the same collision from the consumer side.

The intended posture is unchanged and stays a rule, not a feature: one conductor per clone. This spec only makes the second conductor fail loudly instead of silently stealing.

## Architecture & Data Models
<!-- scope: technical -->

One deterministic change in the start verb, no new identity, no persisted token:

- A same-actor `in_progress` task refuses `flowctl start` with a typed contention error, exactly as a foreign claim does today, unless `--reclaim` is passed. `--reclaim` already exists as the deliberate identity repair; it becomes the one explicit resume path. `--force` keeps its current meaning.
- The callers that legitimately resume already gate on evidence before they do: work's direct-owner resume admission requires a matching claim plus positive evidence the prior invocation ended, and `flow --auto`'s stale-claim row does the same. Those paths pass `--reclaim` after their check instead of relying on the email coincidence. The `ready`/`next` listing keeps reporting an own in-progress task as resumable; only the claim write refuses.
- The rolling scheduler's notes pointer is keyed by the `RUN_ID` it already mints (timestamp plus pid), so two concurrent runs on one checkout no longer overwrite each other's pointer or delete each other's live notes directory.

## API Contracts
<!-- scope: technical -->

`flowctl start <task>` on an `in_progress` task assigned to the current actor, without `--reclaim`: non-zero exit, JSON error naming the task, the claimant, and the two ways forward (`--reclaim` after confirming the prior run ended, or leave it). With `--reclaim`: current behaviour. Foreign-claim behaviour is untouched. No new flags, no new config keys, no new files.

## Edge Cases & Constraints
<!-- scope: technical -->

- A crashed run re-invoked in a fresh session must still recover in one step: the skill prose's existing evidence check followed by `--reclaim`. A user running `flowctl start` by hand on their own stuck task reads the error and adds the flag.
- `--reclaim` remains a human or skill decision, never applied automatically by a driver without the evidence check.
- Cross-worktree: claims live in the shared flow-state directory, so the refusal covers worktrees of one clone. A second clone has its own state and is outside this spec, as today.
- No heartbeats, leases, per-machine actors, or stale-claim reaping. Age proves nothing and is not consulted.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A second same-actor `flowctl start` on an `in_progress` task refuses with a typed contention error; the same call with `--reclaim` succeeds; a foreign claim behaves exactly as before. Focused deterministic tests cover all three. Errors: the refusal itself is the error surface; nothing else changes.
- **R2:** The claim prose in work (direct-owner resume admission, the no-plan route's contention note) and in flow's auto and backlog references states the refuse-by-default semantics and passes `--reclaim` only after the existing evidence check; the Codex mirror regenerates idempotently. Errors: none.
- **R3:** The rolling scheduler's notes pointer is keyed by `RUN_ID`, and a second concurrent run on one checkout neither overwrites the first run's pointer nor removes its notes directory; a focused test covers it. Errors: none.
- **R4:** The changelog entry states the behaviour change and the one-step recovery; issues #369 and #370 are re-read against it and closed or narrowed with a comment. Errors: none.

## Boundaries
<!-- scope: business -->

- No per-run identity token, claim schema change, or persisted run id.
- No leases, heartbeats, stale-claim reaping, or multi-runner coordination of any kind; one conductor per clone stays a rule.
- No change to `--force`, to cross-actor behaviour, or to the shared flow-state layout.
- No Worktree Kit changes (#370's print-out is judged after this lands, not built here).

## Decision Context
<!-- scope: both -->

**Why a refusal flip rather than run identities.** The hole is that the second run's `start` cannot tell it is a second run. A refusal makes every same-actor resume explicit, which is the property the token was meant to buy, without minting, persisting, or comparing anything. The strategy reserves deterministic machinery for unattended-trust rails with zero judgment; this is one line of that kind.

**Why `--reclaim` and not a new `--resume`.** The flag exists, already means "I am deliberately taking this claim", and the skills that resume already perform an evidence check before they would pass it. A second flag would be the same decision under a new name.

**Why not coordinate runners properly.** Leases and heartbeats model a multi-runner world this product declines to be; land's one-host-per-clone rule is the same posture. The cost of the refusal is one extra flag on a genuine crash resume; the cost of the alternative is a subsystem.

**Rejected:** the August per-run token (superseded by this shape); actor placeholder rejection from #369 as a separate config leaf (re-evaluate only if the refusal proves insufficient).
