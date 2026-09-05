# One change through review

The useful part of a review is the correction it produces. Flow-Next's own PR #215 connects a performance requirement to an implementation, a review finding, a regression check, and the final handover.

## The requirement

The CLI was spending time repeatedly asking Git for the same repository information. The spec called for caching successful lookups and batching reference searches while preserving their results. R8 required the batched search to keep the same per-symbol attribution, ordering, and reference limits.

The [spec](../../../.flow/specs/fn-109-flowctl-hot-path-perf-memoize-repo-root.md) states those acceptance criteria. They gave review something more precise to check than whether the CLI felt faster.

## What review caught

The review found that a user's forced-color Git configuration could add terminal escape sequences to the batched search output. Parsing that output dropped references, violating the requirement to preserve attribution.

The implementation added `--color=never` to the Git search. The review-round fix (`17f3c3c3ab2086eb6cc4ae2fdcf8094a912679a1`) is a separate commit, so a reader can inspect the correction directly.

## What was checked

The [task record](../../../.flow/tasks/fn-109-flowctl-hot-path-perf-memoize-repo-root.2.md) records the NEEDS_WORK finding and the fix through SHIP. Verification included byte-parity comparisons with the earlier sequential implementation, the focused export tests, the full test suite, and smoke tests.

These are historical results from that change. The old installation paths and test counts in the linked records are evidence of that run, not instructions for a current install.

## What the human received

The PR maps acceptance criteria to tasks and evidence commits. Its review plan specifically points at the forced-color correction and asks whether it fully neutralizes the Git configuration edge case. A reviewer can follow the important change without rediscovering why it exists.

| Question | Where the answer lives |
|---|---|
| What behavior must stay true? | Spec R8 |
| What did review find? | Task record and review-round correction |
| How was the fix checked? | Test evidence and comparison with the previous implementation |
| What should a human inspect? | The PR's requirement coverage and review plan |

That is the evidence chain you should expect from your own run. The requirement identifies the target; the finding changes the implementation; the verification supports the result; the PR makes the remaining review work visible.

See [the root README](../../../README.md) for the linked PR and [architecture](architecture.md#task-completion) for current task evidence.
