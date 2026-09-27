# Defect route (gated reference)

> **Loaded only when** the task fixes a reported defect: flow's defect route, or any spec whose requirement is that reported behaviour stops happening. The worker reads it before writing the fix (worker Phase 1.5). Other tasks never read it.

Four steps, in order. Each one is recorded (see "Record" below), including when it is skipped. Hypotheses, the diagnosis and the fix design are your judgment; flowctl only supplies the git, PR, memory and tracker facts it already reads.

## 1. Prior-fix check, before any fix is written

Look for existing work on this defect in the affected area (the files the symptom runs through):

- open pull requests and branches that change those files (`gh pr list --state open`, `git log <base>..<branch> -- <paths>`);
- recent commits and reverts on those files (`git log -- <paths>`, including `Revert` subjects);
- the memory bug track (`flowctl memory search "<symptom>" --track bug`);
- tracker issues describing the same symptom (`gh issue list --search "<symptom>"`, or the configured tracker).

A source you cannot reach (no network, no `gh` auth, no tracker) is recorded as unchecked with the reason, and the route continues on the rest.

- **An existing fix** (an open PR, a branch, or an unmerged commit that already changes the failing path): run the reproduction against it in a temporary worktree, record the result, and stop. Never write a competing fix.
- **A person visibly owns an in-flight fix** (their open PR, an assigned issue with recent activity): stop and hand back.
- **Several open PRs plausibly touch the area:** stop and list them all.
- **A reverted or recorded-failed attempt:** its stated reason becomes a refuted hypothesis for step 2. Do not retry it unchanged.
- **Nothing found:** continue.

Every stop is the typed escalation `BLOCKED: DEPENDENCY_BLOCKED` naming the PRs, branches or commits and, for an existing fix, whether the reproduction passed against it. Attended, work surfaces it and the user decides; unattended (`flow --auto`, `mode:autonomous`), it becomes `NEEDS_HUMAN` under work's existing rule. Never ask from inside the route.

## 2. Reproduce twice, then diagnose

The symptom reproduces, then reproduces again, before diagnosis starts. When it is flaky, tighten the conditions or add instrumentation until it fires every time. A symptom that will not reproduce is reported as not reproduced, with what was tried, and no fix ships for it (`BLOCKED: SPEC_UNCLEAR`).

Then diagnose before designing the fix:

1. List the candidate causes, with step 1's refuted hypotheses marked as already eliminated.
2. Eliminate candidates one at a time with runtime evidence (instrumentation, logs, a narrowed input), running first the check that rules out the most remaining candidates.
3. Confirm the surviving mechanism with evidence. Reading source can propose a cause; it never confirms one.

Design the fix only after the mechanism is confirmed. Temporary instrumentation does not ship.

## 3. Bisect when a known-good revision exists

When the report or the history names a revision where the behaviour was correct (a tag, a release, "it worked last week"), bisect with the reproduction as the test: a script outside the repository that exits `0` on good, `1` on bad and `125` when a revision cannot be tested.

```bash
git worktree add --detach <tmp-dir> <bad-rev>
git -C <tmp-dir> bisect start <bad-rev> <good-rev>
git -C <tmp-dir> bisect run <script>
git -C <tmp-dir> bisect reset
git worktree remove <tmp-dir>
```

Read the introducing commit and the pull request that carried it (`gh pr list --state merged --search <sha>`). Its intent feeds the fix design, and the commit is cited in the diagnosis.

Skip this step, and record why, when there is no known-good revision, no bisectable history (a new repository, a squashed import, a shallow clone), or no reproduction cheap enough to run once per revision.

## 4. Prove on base and head

When the reproduction is a cheap test, commit it failing before the fix, in its own commit. A reproduction that is expensive or needs a whole integration stack stays preferred rather than required (worker Phase 3).

Run the same reproduction on the base (the revision before the fix: the failing-test commit, or the task's base commit with the reproduction added in a temporary worktree) and on the head:

- It must fail on base and pass on head.
- **It passes on base:** it does not capture this defect. Record that, do not claim the fix, and return to step 2 for a reproduction that does.
- **A live surface** (a web or desktop app): the pre-fix reproduction on the live app is the base observation; repeat it on the head through `flow-next:flow-next-drive`, following the feature file when the spec carries a `resolved_feature` line. When the app cannot be started, the test-level proof stands and the live check is recorded as not run, with the reason.
- **A library with no live surface:** the test alone is the proof.

## Record

Add this block to the done summary. Every line is present; an element that did not happen reads `not done: <reason>` rather than being left out. make-pr summarizes it in the PR briefing; the full record stays with the task.

```text
Defect route:
- prior fixes: <what each source found>; unchecked: <source> (<reason>) | none
- diagnosis: eliminated <cause> (<evidence>); ...; confirmed <mechanism> (<evidence>)
- introduced by: <sha> <subject> (<PR>) | skipped: <reason>
- base: <observation at base sha> | head: <observation at head sha>
- live: <head observation on the app> | not run: <reason> | no live surface
```
