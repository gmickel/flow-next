# Worker handover routes (gated reference)

> **Read by the worker only when its prompt carries `PARALLEL_WAVE: true` or `REVIEW_MODE: host-deferred`**
> (worker.md Phase 0). On both routes the worker returns with the task still `in_progress` and the
> conductor owns review and `flowctl done`. The standard single-worker path never reads this file.
> Each section below names the worker.md phase it changes.

## REVIEW_MODE: host-deferred

`host-deferred` means host review runs at the conductor level after you return - the agent that wrote the code never dispatches or issues its own review verdict. Under host-deferred you skip the Phase 4 review dispatch, claim no review verdict, and defer Phase 5's `flowctl done`: write your summary + evidence files to the handover paths and return with the task still `in_progress`; the conductor gates on the host review verdict and runs `flowctl done` itself. A host-deferred return that reports the task review-passed or `done` has broken this.

## Phase 0: Enter the assigned workspace (FIRST)

Before any `flowctl` or git operation, baseline test, file read, or edit:

- When `PARALLEL_WAVE` is `true`, resolve and enter the exact `WORKSPACE` from
  the prompt without using git, then verify the physical current directory
  matches it:

  ```bash
  EXPECTED_WORKSPACE="$(cd -- "<WORKSPACE>" && pwd -P)" || exit 1
  cd -- "$EXPECTED_WORKSPACE" || exit 1
  test "$(pwd -P)" = "$EXPECTED_WORKSPACE" || exit 1
  ```

  Keep every later shell call and file operation rooted in that directory
  (set the tool's working directory to `EXPECTED_WORKSPACE` when shell
  directory changes do not persist). Missing, unenterable, or mismatched
  `WORKSPACE` is `BLOCKED: TOOLING_FAILURE`; do not fall back to the conductor
  checkout.
- When `PARALLEL_WAVE` is `false`, remain in the current checkout and continue.

Done when: `pwd -P` equals the resolved `WORKSPACE` (parallel-wave), or the run is still in the conductor's checkout (single-worker) — before any flowctl, git, test, read, or edit.

## Phase 1: the conductor owns the claim (parallel wave)

In parallel-wave mode the conductor owns the authoritative task claim. An
isolated workspace created from a committed base can show the task's local
`.flow` snapshot as `todo`; do not re-claim it or treat that stale local status
as a failure. Implement only the prompted task and leave Flow state untouched.

## Phase 4: no review dispatch

**Under `PARALLEL_WAVE: true` this phase's review dispatch does not run.**
The conductor reviews only after it joins the wave and integrates this commit
onto the target branch. A parallel-wave worker that reported a review verdict has
broken this; continue to Phase 5's parallel-wave handover branch.

**Under `REVIEW_MODE: host-deferred` this phase's review dispatch does not run** — the agent that wrote the code never dispatches or issues its own review verdict; the conductor runs the host review after you return. A host-deferred worker that invoked impl-review, reported a verdict, or ran Phase 5's `flowctl done` has broken this — see the Phase 5 host-deferred branch.

## Phase 5: hand over instead of `done`

**parallel-wave branch — DO NOT run `flowctl done`.** When `PARALLEL_WAVE` is
`true`, run the Verify block below, commit the finished task, and write the
summary/evidence to the exact task-unique `HANDOVER_SUMMARY` and
`HANDOVER_EVIDENCE` paths from the prompt. Return the task ID, workspace,
commits, paths, and gate results with the task still `in_progress`. Do not
invoke impl-review, mutate tracker state, invoke plan-sync, integrate the
commit, or select more work. The conductor joins the full wave, integrates,
reviews, updates the evidence for integrated commit IDs, and calls
`flowctl done`.

**host-deferred branch — DO NOT run `flowctl done`.** When `REVIEW_MODE` is `host-deferred`: run the Verify block below as normal (the gates still run), write your summary markdown and evidence JSON to the handover paths (same content you would pass to `done`), and RETURN with the task still `in_progress`. Report the file paths, commits, and gate evidence in your final message. The conductor runs the mandatory host review and calls `flowctl done` itself only on a SHIP verdict — a task must never be `done` before its host review. Every other REVIEW_MODE proceeds through this phase unchanged.

("The Verify block below" is worker.md Phase 5's Verify block; it runs unchanged on both routes.)

**Sandbox-blocked commit:** on a parallel-wave or host-deferred path, never call `flowctl done`: write the
assigned handovers, return `in_progress`, and report the exact workspace plus
uncommitted state so the conductor can recover and commit it.

On parallel-wave and host-deferred routes, write the evidence file to the resolved task-unique `HANDOVER_EVIDENCE` path.
For those two routes, re-read `BASE_COMMIT` from the persisted file and compute the FULL commit list
(`BASE_COMMIT`..HEAD, oldest first, so multi-commit fix-loop tasks are covered)
in the SAME block, so no shell variable has to survive across tool calls.
`base_commit` is an additive evidence field — always include it. Include any
`GATE_SKIPPED` lines recorded during this task as plain strings in `tests[]`
alongside real command strings (plain-string schema - no new fields or
objects), and echo those `GATE_SKIPPED` lines verbatim in the worker summary:
```bash
BASE_COMMIT=$(cat .flow/tmp/base_commit)
COMMITS_JSON=$(git rev-list --reverse "$BASE_COMMIT"..HEAD | jq -R . | jq -s -c .)
EVIDENCE_FILE="<resolved task-unique HANDOVER_EVIDENCE path>"
# One quoted argument per test command or GATE_SKIPPED line; jq escapes them.
jq -n --argjson commits "$COMMITS_JSON" --arg base "$BASE_COMMIT" \
  '{commits: $commits, base_commit: $base, tests: $ARGS.positional, prs: []}' \
  --args '<actual test command>' '<GATE_SKIPPED line>' > "$EVIDENCE_FILE"
```

Then write the summary file exactly as worker.md Phase 5 describes, and return before its `flowctl done` command.

## Terminal contract

When `PARALLEL_WAVE` is `true`, the terminal contract is only: green Verify
gates, committed task code, task-unique summary/evidence handovers, and a return
with status still `in_progress`. Do not run impl-review or `flowctl done`; the
conductor owns both after integration. The existing host-deferred exception
likewise returns `in_progress` for the conductor's review.
