# Tail rule (routing reference 6 of 6)

**Decision record**

- Source: the maintainer's boundary that merge and spec close are a human's or land's act, never the attended conductor's.
- Trigger: a flow run reaches all-tasks-done, or starts on a spec that already has an open PR.
- Purpose: state where an attended run ends and what convergence means, so flow never runs on into a merge.
- Evidence: the draft PR and its evidence do not grant merge approval; land carries the only standing merge license, bounded by its gates.
- Disposition: keep.

## A run from intent ends when the PR exists

After the last stage passes its gates and QA has run or recorded its skip, flow runs `/flow-next:make-pr <spec-id>` and the run ends. The report names the PR URL, every stage's `ran` / `skipped(reason)` line, and the human decisions that remain (review the PR, merge, close).

## A run on a spec with an open PR converges it

1. `/flow-next:resolve-pr <PR#>` for unresolved review threads.
2. CI fixes for failures the change caused, within the repo's repair budget; an inherited red is reported, never worked around.
3. Re-review through the configured backend when the fix loop changed code.
4. Re-evaluate: more threads or a new red repeat the cycle; a green, converged PR stops the run.

Flow stops when merge is the only step left and asks before any merge. It never merges on its own, never closes the spec, and never dispatches `/flow-next:land` or a second driver (`/flow-next:flow --auto`). Merge and spec close happen only on an explicit instruction inside the run, or through land.
