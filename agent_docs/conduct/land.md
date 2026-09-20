# Conduct checklist - /flow-next:land

A run resolves and lands one named pull request under current session authorization. The skill and its workflow own the detailed gates; this checklist checks their observable boundaries.

- [ ] Exactly one terminal `LAND_VERDICT=<verdict|NO_WORK> prs=<n> pr=<url|-> reason="<one line>"` is last. `RELEASED` remains parseable but is never emitted. The named resolved PR uses `prs=1`; no resolved target uses `prs=0 pr=-`.
- [ ] Missing or ambiguous input stops with its reason. A closed-unmerged PR is never replaced, reopened, or merged. The run asks no questions and invokes no driver.
- [ ] Land reads every spec at the full remote PR head and selects by `branch_name == headRefName`. At least one must match and all must be closed. An open match changes nothing; a failed or incomplete read is not an empty match.
- [ ] Conflicts stop with the branch needing a rebase. Threads dispatch autonomous resolve-pr before CI repair. Behind branches catch up server-side without rebase. A refused catch-up stops; land never rebases, force-pushes, retargets, or checks out a branch in the invoking checkout.
- [ ] A code CI failure gets one fix and a flake one rerun. Commits and check attempts prevent spending the same budget again; an identical second failure is not a flake. Failed fixes name the check.
- [ ] Merge requires current authorization for this PR, green checks, a nonblocking review decision, and zero unresolved threads. No reviewer activity is required where the repository requires none. Stricter instructions and branch protection remain authoritative.
- [ ] Without human in-session merge authorization, a flow-authorized merge waits `land.patienceMinutes` after the last push. A configured `land.mergeVerdictCommand` runs once only when other gates pass; non-zero, missing, unexecutable, and timed-out commands refuse the merge.
- [ ] The squash merge is pinned to the full current head SHA. A moved head is re-read and reported for fresh gating, never silently substituted into a retry.
- [ ] Open children are linked into a native stack before merging where supported. Only the lowest open layer merges, via the asynchronous call. A branch still targeted by any open PR is retained. Stack branch deletion happens separately after confirmed merge and a fresh successful child check.
- [ ] Where stacks are unavailable, a conflicted child is reported as needing a manual rebase. No local cascade, patch-id carry-over, or pending-deletion file is created.
- [ ] After merge, land writes no repository file, commit, or push. The configured tracker touchpoint preserves current restrictions; its failure reports the merge commit and retains `MERGED`. A merged replay repeats only that touchpoint.
- [ ] Retired `land.*` keys produce one notice naming ignored keys and do not fail config loading. Land owns no ledger, claim, or release step.
- [ ] `--dry-run` reads and reports only: no repair, catch-up, stack creation, verdict command, merge, branch deletion, or tracker mutation.
