---
satisfies: [R1]
---
# fn-167-bugbot-pre-push-review-stage.1 Smoke test: verify patch-ID dedup and PR findings visibility (MANUAL, human-run)

## Description
HUMAN-RUN experiment. Do not implement anything in this task. Its only job is to reach 100% confidence on how `/review-bugbot` actually behaves against a real GitHub PR, because two unknowns decide the design and both are cheap to answer manually and expensive to get wrong in code:

1. Does the patch-ID dedup actually fire on a real PR carrying an identical diff?
2. Do the local review's findings render on the PR, or do they stay in the local agent session?

Answer 2 decides whether `make-pr` changes at all. Answer 1 is the spec's load-bearing premise.

### Setup

- A throwaway repo (or a low-stakes branch) with the Bugbot GitHub App installed and Cursor 3.7+ driving.
- Confirm Bugbot personal settings before starting and record them: 'run only when mentioned', 'run only once', Incremental Review, effort level. They change what you observe.
- Prepare a diff with at least one unambiguous, real bug so findings are guaranteed non-empty, plus one clean file so you can tell a partial review from a full one. A cross-file bug is the highest-value probe.

### Procedure

1. Commit everything. Confirm a clean tree (`git status --porcelain` empty).
2. Record the branch diff's patch ID: `git diff <base>...HEAD | git patch-id --stable`.
3. Run `/review-bugbot` from the Cursor agent against the branch. Record the findings it returns locally: count, severity shape, whether inline locations are included.
4. Push the branch and open a PR carrying the identical diff. Add no further commits.
5. Observe and capture on the PR:
   - Does Bugbot post a review, or skip?
   - The skip comment, verbatim.
   - Do the local findings appear on the PR (inline comments, review body, or not at all)?
   - The `Cursor Bugbot` check conclusion: success / neutral / failure.
   - Whether a separate `Cursor Bugbot Autofix` check appears.

### Invariant probes (the two edges)

6. Push one further trivial commit to the same PR. Confirm a fresh review fires. This proves invariant 1 empirically: anything that commits between the local review and the push kills the dedup.
7. Repeat steps 2-5 with a dirty tree (uncommitted changes present at review time). `/review-bugbot` defaults to reviewing committed AND uncommitted changes, so confirm the resulting patch ID does not match the pushed diff and the dedup does not fire. This proves invariant 2.

### Record

Write findings into the spec's artifacts: PR URL, the verbatim skip comment, the check conclusion, a yes/no on findings visibility, and the two invariant results. Set the eventual receipt field `findings_visible_on_pr` from this.

### Hard stop

If the dedup does not fire on an identical diff, the spec's premise is void. Record the finding, do not start task 2 or 3, and bring it back for a re-decision.

## Acceptance
- Evidence captured for a real PR: URL, verbatim skip comment, `Cursor Bugbot` check conclusion.
- A definitive yes/no on whether local `/review-bugbot` findings render on the PR, with evidence.
- Invariant 1 confirmed: a further commit after the local review triggers a fresh remote review.
- Invariant 2 confirmed: a dirty tree at review time produces a non-matching patch ID and no dedup.
- Bugbot settings in force during the test are recorded alongside the results.
- Explicit go / no-go on the spec premise recorded in the spec artifacts.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
