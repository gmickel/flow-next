# land: merge-identity seam, server-side catch-up, tail persistence (#337, #342, #345)

## Goal & Context

Three @sn-furali land issues, all verified against main, all fixable with ZERO new config keys:

- **#337.** Phase 3.5 merges with a literal `gh pr merge` (workflow.md ~:568) - no identity indirection, while the create side has had one since 3.11.0 (`FLOW_PR_CREATE_CMD`, #277, env-only, seven files). Per-tick identity switching cannot work (the tick also pushes, comments, labels, reruns CI). The seam must be ENV, never a `land.*` key: fn-188's own trust guard proved config-sourced command strings are PR-author-influenceable on a non-base checkout, session env is not. Critical subtlety the issue understates: 3.5 captures STDERR ONLY and classifies head-race-vs-policy (RESOLVING vs BLOCKED) by matching gh's stderr text (~:568, :577) - a wrapper that swallows stderr silently converts benign races into BLOCKED; the seam contract must state verbatim stderr proxying.
- **#342.** `mergeStateStatus == BEHIND` plans `rebase` (~:389); §3.3 rebases + `git push --force-with-lease` (~:522-531) and writes `land_pushed_sha`. On repos that dismiss stale approvals on push, the catch-up itself voids the approval; under `reviewSignal: approve` the loop never converges autonomously (the reporter's §2.7-labels-forever path is PARTIAL - §2.6 may shadow the detector under `approve` and loop AWAITING_REVIEW/NEEDS_HUMAN unlabeled; either way: non-convergence confirmed). The rebase also rewrites every commit SHA - the CAUSE of #302's orphaned evidence (detection shipped in 3.26.0; prevention did not). Fix: NOT the requested `land.catchUp` key - land always squash-merges, so branch-local linearity is invisible after merge; a key would buy a forever contract for an unobservable property. Instead the catch-up becomes unconditionally server-side: `gh pr update-branch` (merge-based, one API call, no local checkout, no force-push). This removes land's force-push capability entirely, removes the #302 cause for every repo, and is a tick speed-up. `DIRTY` routes to the same action (GitHub refuses when the merge would conflict -> BLOCKED), resolving the local-rebase-disagrees-with-mergeStateStatus surprise.
- **#345 (Part A only).** The post-merge tail runs from the base checkout and persists the spec close by committing and pushing to the BASE (~:596-601); on a base that requires PRs the push is refused, land rolls back and skips release-follow AND the tracker touchpoint - so the board sticks at In Review after a real merge, the exact outcome `land.merged` exists to prevent (~:617). A second base-push at ~:673 (tracker sync state) has the same problem. Fix: reorder the tail - spec close (local) -> release-follow -> tracker touchpoint -> persist+push (rollback on failure only affects bookkeeping). Verified safe: release-follow's precondition is a clean non-.flow tree (the close is committed); the tracker projection is gated on a fresh MERGED probe (~:632-644), not on the close being pushed; verdict comments dedupe on the merge-commit identity (~:652). Residue on a PR-only base: a cosmetic per-spec "spec close not pushed" NEEDS_HUMAN instead of a broken lifecycle. Part B (`land.closeVia: pull-request` + close-PR ledger completion) is deliberately HELD - it is the only thing in this batch that would add a config key; the issue reply states the reopen condition (residual chore still blocking after Part A).
- **Found during verification (ship it):** §2.6/§2.7 ordering is ambiguous - whether the stale-approval detector (~:383) is reachable under `reviewSignal: approve` or shadowed by §2.6's earlier exit. One clarifying paragraph stating the evaluation order.

Sequencing: open spec fn-149 (land hardening) rewrites the same §2.8/§3.3/§3.5 region - THIS spec lands first; fn-149's R8 (mechanical-rebase conflict rule) must be amended when fn-149 runs (note it in fn-149's spec file as part of close-out here).

## Acceptance Criteria

- R1: §3.5's merge call honors `FLOW_PR_MERGE_CMD` (default `gh pr merge`), #277-shape (whitespace-split, never eval'd), with an inline contract block: fixed argument order (`<pr> --squash --delete-branch --match-head-commit <sha>`), exit 0 = merged, stderr proxied VERBATIM (or the RESOLVING/BLOCKED split degrades - stated), never `--auto`/merge-queue, scope is the merge call only (gh pr ready, post-merge reads, tail, and all other gh calls stay on the session identity).
- R2: the BEHIND and DIRTY paths both plan a `catch-up` action executed as `gh pr update-branch "$PR_NUMBER"`; non-zero -> BLOCKED with a conflicts-need-hand-resolution reason. The local rebase + force-push block is REMOVED; the post-catch-up ledger write sources the new SHA from `gh pr view --json headRefOid`. The `rebase` action class is renamed `catch-up` everywhere it appears (§2.8, §3.3, Phase 4 action enum, SKILL.md, PLANNED_ACTION list); SKILL.md's "mechanical rebase only" safety line restates as server-side catch-up only.
- R3: the post-merge tail order becomes: spec close (local commit) -> release-follow -> tracker touchpoint -> persist+push with rollback; the ~:673 sync-state push moves inside the same persist step or gains the same failure isolation; a failed persist no longer skips release-follow or the tracker touchpoint; §3.6 re-entry prose updated to match.
- R4: one paragraph clarifies §2.6/§2.7 evaluation order under `reviewSignal: approve` (which gate wins and why).
- R5: conduct checklist (agent_docs/conduct/land.md) updated: the merge line binds the seam ("however the merge is executed..."); a tail line states the new order and that release/tracker precede the persist-push.
- R6: static workflow tests in test_land_config.py's existing style: seam present with the contract tokens (FLOW_PR_MERGE_CMD, --match-head-commit, never --auto); no `git rebase`/`--force-with-lease` remains in the land workflow; update-branch present with BLOCKED routing; tail order pinned by ordering assertions (close before release-follow before tracker before push); §2.9/fn-188 pins stay green.
- R7: docs: docs/README.md + docs/skills.md list FLOW_PR_MERGE_CMD next to FLOW_PR_CREATE_CMD; troubleshooting note for the catch-up change; CHANGELOG Unreleased credits @sn-furali; fn-149 spec file gains a one-line amendment note re R8.

## Boundaries

- ZERO new config keys (Part B held; catchUp key rejected - rationale in Goal & Context).
- No flowctl Python changes at all in this spec.
- The §2.9 merge-verdict gate, its trust guard, and the (head, base) binding are untouched (R1's seam sits strictly downstream of the head pin).
- Merge-license boundary unchanged (explicit squash, never --auto - now also binding the interposed command).
- sync-codex x2 after every prose change; no version bump in implementation commits.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_land_config test_skill_prose_diet -q
```
