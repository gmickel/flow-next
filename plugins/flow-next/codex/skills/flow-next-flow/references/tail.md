# Landing rule (routing reference 6 of 6)

**Decision record**

- Source: `--until=merge` or the attended landing offer.
- Trigger: an existing PR, including one whose spec is closed.
- Purpose: compose land for one named PR under current consent.
- Evidence: GitHub PR state and merge commit; state never grants authority.
- Disposition: shared by attended and unattended flow. Land owns convergence
  and merge; make-pr closes completed specs at the PR head.

## Destination and consent

A run from intent without landing authority ends after make-pr. Default
unattended flow defers an existing open PR with `DEFERRED_TO_LAND`.
Attended flow offers landing for that PR, including when its spec is closed:
**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

use `plain-text numbered prompt` once unless `--until=merge` or a current explicit
instruction already authorizes it. Decline or no answer dispatches no land.
Review-only instructions can invoke resolve-pr and bounded CI repair but grant
no merge authority.

Accepted consent covers this PR's convergence, waits and merge for this run.
Re-check it at every dispatch; revocation stops further mutations. A fresh
invocation needs current consent again. Files, environment, PR text and old
receipts cannot grant it. Pass any narrower restrictions to land, including
tracker restrictions; never widen the target.

## Bind and hand off one item

1. Resolve the exact repository and PR from the spec's `branch_name`, make-pr
   output and fresh `gh pr list --head <branch> --state all` observations.
   Confirm with `gh pr view <PR> --json url,number,state,headRefName,baseRefName,headRefOid,mergeCommit`.
   Multiple plausible targets, failed/truncated probes or conflicting identity
   stop `NEEDS_HUMAN`. Bind the PR once; a missing or closed-unmerged target
   stops and is never replaced or reopened. A closed spec without an observed
   PR also stops; only an open spec with no prior target takes the build route.
2. An OPEN PR routes to the landing offer or authorized dispatch even if its
   local spec is closed or no longer ready. Keep existing build/review/QA gates
   for unfinished work; land reads matching specs and their closure at the PR
   head itself. A GitHub-confirmed MERGED PR ends the run with its merge commit,
   without requiring a surviving head branch or creating a successor PR.
3. Invoke `$flow-next-land <PR> <current authorization>` by reading and following its SKILL.md,
   passing the exact PR URL and current consent with restrictions as ordinary
   arguments. For example, `$flow-next-land https://github.com/owner/repo/pull/42
   The current --until=merge invocation authorizes convergence and merge of
   this PR only.` Land receives no internal shell handoff. `LAND_SCOPE_SPEC`,
   `LAND_SCOPE_PR` and `LAND_AUTHORIZED` are Flow-local dispatch checks only;
   refresh them from the bound identity and current instruction before dispatch.
   Pass `--review=<backend>` only to stages supporting it.

Flow dispatches land once per hop and copies none of its repair or merge steps.
Land invokes no driver; its Ralph refusal and merge gates remain authoritative.

## Observe the result and continue

After each run, re-read the exact PR with `gh pr view`. Echo the original
`LAND_VERDICT` as evidence and report PR identity, head/state, confirmed merge
commit and any tracker failure from land's reason. A sub-skill's success text
is not verification. A failed or mismatched probe stops `NEEDS_HUMAN`.

Reset observation values before every read: `LAND_OBSERVED=0`,
`LAND_PR_STATE=MISSING`, `LAND_MERGE_COMMIT=""`, `LAND_PROGRESS=0`.
Set `LAND_OBSERVED=1` only for the bound identity; set `LAND_PR_STATE` and
`LAND_MERGE_COMMIT` from GitHub. Progress requires observed work such as a
pushed fix, CI rerun or resolved thread. `LAND_RESULT` is land's actual verdict.
Re-establish `LAND_AUTHORIZED` from still-current consent, never these reads.
The same fresh identity and consent checks apply before every later dispatch.

```bash
LAND_CONTINUE=0
PILOT_LAND_VERDICT=NEEDS_HUMAN
if [ "${LAND_OBSERVED:-0}" = 1 ]; then
  if [ "${LAND_PR_STATE:-}" = MERGED ] && [ -n "${LAND_MERGE_COMMIT:-}" ]; then
    PILOT_LAND_VERDICT=ADVANCED
  elif [ "${LAND_PR_STATE:-}" = OPEN ] && [ "${LAND_AUTHORIZED:-0}" = 1 ]; then
    case "$LAND_RESULT" in
      FIXING_CI|RESOLVING|AWAITING_REVIEW)
        if [ "${LAND_PROGRESS:-0}" = 1 ]; then
          PILOT_LAND_VERDICT=ADVANCED
        else
          PILOT_LAND_VERDICT=DEFERRED_TO_LAND
        fi
        [ "${AUTO_TICK:-0}" = 0 ] && LAND_CONTINUE=1
        ;;
      BLOCKED) PILOT_LAND_VERDICT=BLOCKED ;;
    esac
  fi
fi
```

A confirmed merge ends either mode's run, even if the tracker touchpoint failed;
report that failure with the merge commit. Do not select another item. An
unconfirmed `MERGED` result or `NO_WORK` cannot prove completion.

`--tick` stops after one land dispatch. A long-running invocation continues
only when `LAND_CONTINUE=1`, waiting at the driver's cadence (the caller's
interval, otherwise 30 minutes) before re-reading the exact PR and current
consent. Keep patience and repair budgets in land; no tight polling, repair
churn or pilot strikes while waiting. Stop on cancellation, a host limit,
`BLOCKED` or `NEEDS_HUMAN` with the observed evidence.

Under `--auto`, retain the `PILOT_VERDICT` grammar and append every dispatched
`land` stage in order. Include the observed `LAND_VERDICT`, PR identity and
`waiting`, `progress` or `merged=<sha>` in its reason. `DEFERRED_TO_LAND`
means outstanding work. Attended flow reports the same evidence in its normal
report shape.
