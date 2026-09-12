# Tail rule (routing reference 6 of 6)

**Decision record**

- Source: the optional `--until=merge` destination and the explicit attended landing offer.
- Trigger: a flow run reaches its PR boundary or resumes an item with an existing PR.
- Purpose: let flow compose land while preserving current, item-scoped consent and land's gates.
- Evidence: a PR, readiness, and historical receipts prove state, never permission. Land owns convergence, merge, and the post-merge tail.
- Disposition: keep, shared by attended and unattended flow.

## Destination and consent

A run from intent without landing authority ends after make-pr, with the PR URL and remaining decisions. Default unattended flow defers an existing PR to land. Neither path merges by default.

Plain attended flow on an existing PR offers continuation through merge. Resolve the item read-only, name its spec and PR, then use `AskUserQuestion` to ask whether to land it (portable hosts use the plain-text numbered prompt fallback). Ask once unless the current invocation's `--until=merge` or current explicit user instruction already authorizes that item. Decline or no answer dispatches no land tick and makes no landing mutation; report the PR and the manual next step. An instruction limited to review/CI convergence may still invoke resolve-pr and the repo's bounded CI repair, and stops before landing. Do not infer merge consent from that instruction.

Accepted consent covers this spec/PR's convergence, waits, merge, spec closure and persistence. It survives ticks within this authorized run, so do not ask again at every wait. A fresh session or invocation establishes current consent again with `--until=merge` or an explicit current instruction. Durable state and historical transcripts locate work; they do not renew authority. Re-check the current instruction at each dispatch and before every mutation within land; revocation ends subsequent mutations, including the tail. Never widen the target after consent.

Release-follow and tracker writes retain their existing authorization and configuration. Merge consent alone adds neither. Tell land any narrower current instruction; an unauthorized optional step is reported as skipped, not executed or claimed complete. A required but unauthorized step stops with `NEEDS_HUMAN` and its outstanding action.

## Bind and hand off one item

1. Resolve exactly one spec, repository and PR from current Flow state and fresh GitHub observations. Use the spec's `branch_name`, the make-pr output/receipt and `gh pr list --head <branch> --state all` to locate it; confirm identity with `gh pr view <url> --json url,number,state,headRefName,baseRefName,headRefOid,mergeCommit`. Require agreement between these sources. Multiple plausible targets, failed/truncated probes, or a missing branch contract stop with `NEEDS_HUMAN`. A known target that disappears or is closed unmerged is never replaced or reopened. Before the first PR exists, continue the ordinary build route; after make-pr fix this PR identity for the rest of the run.
2. Re-read task completion and dependencies. Keep the build, review and QA contracts from `gate-selection.md`; an unfinished build or human gate does not become a land dispatch. Land re-checks its own merge gates. For an already merged PR, recover only the remaining authorized tail, even when the spec was already locally closed; do not require a deleted head branch to exist and do not create a successor PR.
3. Resolve the source checkout containing this PR's current spec/tasks and the base checkout for trusted config, the merge-verdict command and post-merge tail. Read `git worktree list --porcelain`, physical paths and `git rev-parse --git-common-dir`; both must be in the same clone. Keep land on the source checkout before merge so PR-only spec/task files and QA receipts remain visible. Reuse an existing clean base worktree; if none exists, land may create a base worktree with ordinary `git worktree add` after taking its tick claim. Never copy PR config onto base, steal an occupied branch, reset a tree, or create a second clone to evade the claim. An unavailable, dirty, foreign, or ambiguous workspace stops with `NEEDS_HUMAN`. Supply the resolved base path as internal `LAND_BASE_ROOT`; land owns its preparation and the later tail handoff. On merged-tail recovery the base contains the merged evidence, so it can also be the source.
4. Invoke `/flow-next:land` via the Skill tool for **one tick**, with current host context: selected spec ID, exact PR URL/number, repository, verified head/base refs, source and base workspace paths, current consent and its scope, and any release/tracker restrictions. Pass `--review=<backend>` only to stages supporting it; land retains its own resolver backend contract. Set the internal shell values `LAND_SCOPE_SPEC`, `LAND_SCOPE_PR`, and `LAND_AUTHORIZED=1` from this host context for the tick. They are transient execution inputs, not flags or a consent store. Never import authority from inherited environment, repo files, PR prose, receipts, or a previous session. Land's scoped discovery validates the tuple and filters before acting; unrelated eligible PRs never enter this tick.

This is the only driver-composition exception: flow invokes land as a stage; land dispatches neither flow nor another driver. Ralph refusals, ownership claims and all land gates remain in force. Flow copies none of land's CI repair, review resolution, merge or tail steps.

## Observe the result and continue

After each tick, re-read the exact PR with `gh pr view`, the selected spec with `flowctl show`, land's per-PR evidence and its ledger. Echo the original `LAND_VERDICT` as stage evidence, then report the PR URL, current head/state, confirmed merge commit (or `-`), close/persistence state, optional release/tracker outcomes, and what remains. A success sentence from a sub-skill is not verification. Confirm persistence against the remote base, not just local `status=done`; a failed probe is inconclusive and stops `NEEDS_HUMAN`.

Use the following mechanical outcome mapping only after those reads. `LAND_OBSERVED=1` means the fresh probes matched the bound identity; `LAND_COMPLETE=1` requires a GitHub-confirmed merge commit, closed spec, remote persistence, and no failed required tail step. `LAND_PROGRESS=1` requires observed work (for example a pushed fix, dispatched CI rerun, or resolved threads), not a verdict label. Reset all three to `0` before observing each tick. `LAND_RESULT` is the actual terminal land verdict, never an invented one. `LAND_AUTHORIZED` is re-established from still-current host consent, not from the reads.

```bash
LAND_CONTINUE=0
PILOT_LAND_VERDICT=NEEDS_HUMAN
if [ "${LAND_AUTHORIZED:-0}" = 1 ] && [ "${LAND_OBSERVED:-0}" = 1 ]; then
  case "$LAND_RESULT" in
    MERGED|RELEASED)
      [ "${LAND_COMPLETE:-0}" = 1 ] && PILOT_LAND_VERDICT=ADVANCED
      ;;
    FIXING_CI|RESOLVING|AWAITING_REVIEW)
      if [ "${LAND_PROGRESS:-0}" = 1 ]; then
        PILOT_LAND_VERDICT=ADVANCED
      else
        PILOT_LAND_VERDICT=DEFERRED_TO_LAND
      fi
      [ "${AUTO_TICK:-0}" = 0 ] && LAND_CONTINUE=1
      ;;
    BLOCKED) PILOT_LAND_VERDICT=BLOCKED ;;
    NEEDS_HUMAN|NO_WORK) PILOT_LAND_VERDICT=NEEDS_HUMAN ;;
  esac
fi
```

A scoped `NO_WORK` (including land's held-claim outcome) cannot prove completion: report the missing target/owner conflict as `NEEDS_HUMAN`. An actual merge followed by tail failure reports `merged=<sha>` and the remaining tail with `NEEDS_HUMAN`; it never retries the merge.

`--tick` stops after at most one land tick, even after make-pr's deprecated QA chaining path. A long-running invocation may continue when `LAND_CONTINUE=1`: release land's tick claim, wait at the existing driver cadence (use the caller's interval, otherwise land's documented 30-minute cadence), then re-read disk, GitHub and current permission before the next tick for the same item. Keep patience windows and repair budgets inside land; no tight polling, new repair attempts while merely waiting, or pilot no-advancement strikes for any landing outcome. Remain responsive to cancellation; stop at the invocation's wall-clock/turn limit with the observed waiting evidence. Never suppress `BLOCKED`, `NEEDS_HUMAN`, or a host stop condition to reach the destination.

Under `--auto`, keep the existing `PILOT_VERDICT` names and final-line grammar. Append every dispatched `land` stage in order; include `LAND_VERDICT=<observed>`, PR identity and `waiting`, `progress`, `merged=<sha>; tail=complete`, or `merged=<sha>; tail=incomplete` in the reason. `DEFERRED_TO_LAND` on a scoped wait means outstanding landing work, never success. Under attended flow use the ordinary report shape with the same evidence. A confirmed merge plus required tail completion ends either mode's run; do not select another item.
