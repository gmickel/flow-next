---
satisfies: [R1, R2, R3, R4]
---
# fn-204-same-actor-claim-contention-refuse-by.1 Implement Same-actor claim contention: refuse by default, resume by explicit reclaim

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
`flowctl start` now refuses an `in_progress` task held by the current actor unless `--reclaim` is passed (error names the task, the claimant, and both ways forward; `--force` and foreign-claim behaviour unchanged), the work/flow resume prose passes `--reclaim` only after the existing evidence check, the rolling scheduler's notes pointer is keyed by `RUN_ID` so two concurrent runs on one checkout keep separate pointers and cleanup, and the changelog carries the behaviour change plus one-step recovery. Codex mirror regenerated twice, idempotent.

baseline: green (full suite 4991 ran / 0 failures, ruff clean at e0cee32b)

Tests: `test_start_reclaim.py` (+3: same-actor refusal, `--reclaim` resume, `--force` keeps meaning; foreign-claim case pre-existing) covers R1; `test_rolling_notes_pointer.py` (+2, executes the skill's 3.0 and 3f bash fences) covers R3. Both were run red-first against the pre-edit behaviour.

stage: impl-review - ran (codex gpt-6-astra high; round 1 fan-out NEEDS_WORK on one duplicated paragraph, round 2 SHIP)

### R4 issue follow-up (maintainer posts after release; the worker did not touch GitHub)

**#369 - recommended disposition: close.** Comment text:

> fn-204 landed in a different shape than the per-run token I described here: instead of minting a run identity, `flowctl start` now refuses an `in_progress` task held by the current actor unless `--reclaim` is passed, exactly as it refuses a foreign claim. The default outcome this issue describes - a second runner resolving to the same actor and silently resuming the first one's claim - no longer happens; the second `start` exits non-zero and names the task and claimant. The resume paths in work and `flow --auto` pass `--reclaim` only after their existing evidence that the prior run ended, so nothing infers termination from a claim's age.
>
> I'm closing this on that basis. The refusal seam itself stays unbuilt: its job was compensating for non-unique actors, and with same-actor claims refused by default it has no remaining case I can see. If a repository-level refusal for placeholder or machine-wide identities still earns its place after you've run on this, open it as its own proposal and I'll look at the `cmd_start` config leaf first.

**#370 - recommended disposition: narrow (or close), maintainer's call after judging the post-fn-204 behaviour.** Comment text:

> fn-204 landed: `flowctl start` now refuses an `in_progress` task held by the current actor unless `--reclaim` is passed, so two sibling worktrees sharing a git email can no longer resume each other's work by default, whether or not anyone configured a per-runner actor. The collision this issue opens with is gone.
>
> What remains is the narrower ask: whether printing the resolved actor at `create` still adds signal now that a shared identity fails loudly instead of silently. I'm narrowing this issue to that question and will judge it against the post-fn-204 behaviour rather than build it now; surface-never-set stays the constraint either way.
## Evidence
- Commits: 8a8c78139637dcafbb35becf35c1845a79e367b9, ca5a61ff7543d06eb2eafbad3d587e730a700cf3
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., python3 -m unittest test_start_reclaim (plugins/flow-next/tests), python3 -m unittest test_rolling_notes_pointer (plugins/flow-next/tests), ./scripts/sync-codex.sh x2 (idempotent)
- PRs: