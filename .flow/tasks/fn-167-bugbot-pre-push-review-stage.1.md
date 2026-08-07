---
satisfies: [R1]
---
# fn-167-bugbot-pre-push-review-stage.1 Smoke test: verify patch-ID dedup and PR findings visibility (MANUAL, human-run)

## Description
### Entry point (prebuilt 2026-08-07 by task .4)

Everything is staged: branches `fn-167-smoke/bugbot-target` + `fn-167-smoke/bugbot-dedup` (byte-identical patch-id `6c49a82a`), deliberate-bug fixture `scratch/bugbot-smoke/queue-drain.js` (3 reviewer-visible bugs), zero CI triggers on the diff. **Follow `scratch/bugbot-smoke/RUNBOOK.md` on the target branch** - it condenses this task to 7 numbered steps (settings record, enable, probes A-D, record, revert).


### Description
HUMAN-RUN experiment. Do not implement anything in this task. Its only job is to reach 100% confidence on how `/review-bugbot` actually behaves against a real GitHub PR, because three unknowns decide the design and all are cheap to answer manually and expensive to get wrong in code:

1. Does the patch-ID dedup actually fire on a real PR carrying an identical diff?
2. Do the local review's findings render on the PR, or do they stay in the local agent session?
3. What happens on a **draft** PR, given `make-pr` forces `--draft` under `mode:autonomous` and Bugbot's "Review Draft PRs" is off by default?

Answer 2 decides whether `make-pr` changes at all. Answer 1 is the spec's load-bearing premise. Answer 3 decides whether the stage's primary justification is cost (dedup) or coverage (the only path to Bugbot eyes on autonomous output).

### Setup: temporary Bugbot activation

Bugbot is currently **disabled** on `gmickel/flow-next` in the Automations tab. Enable it there for the duration of this task, and **revert it when done** -- flow-next runs ~67 PRs/30d and leaving it on would draw heavily from the Cursor included-usage pool.

Record the account settings in force before starting, because they change what you observe. As of writing they are:

- Auto-Enable for New Repositories: off
- Review Draft PRs: **off**
- Run Once Per PR: **on** ("review when opened, ignore new commits")
- Post PR Summary: As Comment
- Post PR risk score: on
- Automatically Learn Rules: on
- Autofix Behavior: **off** (keep it off -- "Commit to Existing Branch" commits after review and would break the patch ID by design)

Note the interaction with "Run Once Per PR": with it on, step 6's further-commit probe should NOT trigger a second remote review. Toggle it off for that probe specifically, then restore it. Record which state was active for each observation.

Also prepare: a branch on `gmickel/flow-next` (or a throwaway repo) with a diff containing at least one unambiguous, real bug so findings are guaranteed non-empty, plus one clean file so a partial review is distinguishable from a full one. A cross-file bug is the highest-value probe, since that is the class Codex's diff-scoped review misses.

### Procedure

1. Commit everything. Confirm a clean tree (`git status --porcelain` empty).
2. Record the branch diff's patch ID: `git diff <base>...HEAD | git patch-id --stable`.
3. Run `/review-bugbot` from the Cursor agent against the branch. Record the findings it returns locally: count, severity shape, whether inline locations are included.
4. Push the branch and open a **non-draft** PR carrying the identical diff. Add no further commits.
5. Observe and capture on the PR:
   - Does Bugbot post a review, or skip?
   - The skip comment, verbatim.
   - Do the local findings appear on the PR (inline comments, review body, or not at all)?
   - The `Cursor Bugbot` check conclusion: success / neutral / failure.
   - Whether the PR summary comment and risk-score block appear, and whether they appear on a skipped review.

### Invariant probes (the two edges)

6. Toggle "Run Once Per PR" **off**, push one further trivial commit to the same PR, confirm a fresh review fires, then restore the setting. This proves invariant 1 empirically: anything that commits between the local review and the push kills the dedup.
7. Repeat steps 2-5 with a dirty tree (uncommitted changes present at review time). `/review-bugbot` defaults to reviewing committed AND uncommitted changes, so confirm the resulting patch ID does not match the pushed diff and the dedup does not fire. This proves invariant 2.

### Draft probe (the third unknown)

8. With "Review Draft PRs" still off, open a **draft** PR from a fresh branch and confirm Bugbot does not review it at all.
9. Run `/review-bugbot` locally against that same draft's diff, then mark the draft ready-for-review without adding commits. Record whether the dedup applies, whether a fresh review fires, or whether nothing happens.
10. Optionally repeat with "Review Draft PRs" on, to characterise both configurations.

### Record

Write findings into the spec's artifacts: PR URLs, the verbatim skip comment, the check conclusions, a yes/no on findings visibility, the two invariant results, and the draft-path behaviour. Set the eventual receipt field `findings_visible_on_pr` from this. Note which Bugbot settings were active for each observation.

### Teardown

Disable Bugbot on `gmickel/flow-next` again. Restore "Run Once Per PR" to on and "Review Draft PRs" to off. Confirm in the Automations tab.

### Hard stop

If the dedup does not fire on an identical diff, the spec's cost premise is void. Record the finding and do not start task 2 or 3 on the cost argument. Note that a null result here does not necessarily kill the spec: if the draft probe shows Bugbot never reviews autonomous pilot output, the coverage argument stands on its own and the spec should be re-scoped around it rather than dropped. Bring it back for a re-decision either way.
### Acceptance
- Bugbot temporarily enabled on `gmickel/flow-next` for the test and **verifiably disabled again** afterwards; account settings restored (Run Once Per PR on, Review Draft PRs off, Autofix off).
- Account settings in force recorded alongside every observation.
- Evidence captured for a real non-draft PR: URL, verbatim skip comment, `Cursor Bugbot` check conclusion.
- A definitive yes/no on whether local `/review-bugbot` findings render on the PR, with evidence.
- Invariant 1 confirmed: with Run Once Per PR off, a further commit after the local review triggers a fresh remote review.
- Invariant 2 confirmed: a dirty tree at review time produces a non-matching patch ID and no dedup.
- Draft path characterised: whether a pilot-forced draft PR is reviewed at all with Review Draft PRs off, and what happens when it is marked ready-for-review without new commits.
- Explicit go / no-go recorded in the spec artifacts, separating the cost premise (dedup) from the coverage premise (draft path), since either can survive alone.
### Done summary
TBD

### Evidence
- Commits:
- Tests:
- PRs:
## Acceptance
- Bugbot temporarily enabled on `gmickel/flow-next` for the test and **verifiably disabled again** afterwards; account settings restored (Run Once Per PR on, Review Draft PRs off, Autofix off).
- Account settings in force recorded alongside every observation.
- Evidence captured for a real non-draft PR: URL, verbatim skip comment, `Cursor Bugbot` check conclusion.
- A definitive yes/no on whether local `/review-bugbot` findings render on the PR, with evidence.
- Invariant 1 confirmed: with Run Once Per PR off, a further commit after the local review triggers a fresh remote review.
- Invariant 2 confirmed: a dirty tree at review time produces a non-matching patch ID and no dedup.
- Draft path characterised: whether a pilot-forced draft PR is reviewed at all with Review Draft PRs off, and what happens when it is marked ready-for-review without new commits.
- Explicit go / no-go recorded in the spec artifacts, separating the cost premise (dedup) from the coverage premise (draft path), since either can survive alone.
## Done summary
Smoke executed 2026-08-07 (Gordon live in Cursor + agent-prebuilt fixtures, 3 fixture iterations). VERDICT: premise falsified - patch-ID dedup does not fire local->PR (fresh full review on identical diff, PR #298). Full observations: .flow/memory knowledge/decisions "Bugbot pre-push stage wont-do" + session memory. Spec closed wont-do as a result.
## Evidence
- Commits:
- Tests: live probes A-C on gmickel/flow-next PRs #297/#298; fixture branches fn-167-smoke/* patch-id-verified
- PRs: