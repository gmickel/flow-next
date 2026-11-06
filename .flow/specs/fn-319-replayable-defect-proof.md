# Replayable defect proof

## Goal & Context

A defect fix is only as convincing as its proof: a test that fails on the unchanged code and passes after the fix, shown to the person in the reply. Our own evals show flow-next's defect proofs often fall short of that, even when the fix itself is right. Across two bug cases and two rounds (12 runs), verification was the lowest-scoring judge criterion on flow-next's defect fixes. [paraphrase]

Four process gaps explain it. [paraphrase]

- **The red cannot be replayed.** Failing tests imported a constant the fix adds. Inside the session they failed by assertion, after the agent exported the constant first. On the unchanged code they only fail to load, so a reviewer or grader replaying the test sees no behavioural failure. [paraphrase]
- **No test-first history.** Attended runs commit only when review needs it, so simple-bug runs ended with no commits at all. When the test was committed first, that commit also carried the fix's new constant, so the history never shows a test-only red. [paraphrase]
- **Evidence missing from the last reply.** After a follow-up, the final reply answers only the follow-up and points back to "the earlier handoff". The person, and anything that reads the final reply, never sees the proof there. [paraphrase]
- **One of two reported symptoms proven.** When a report named two symptoms, the second got its own test in only 2 of 6 runs. [paraphrase]

Separately, one hard-bug run shipped a real defect: a change meant only to coalesce persisted writes also made the in-memory expiry move only once a minute. It failed the hidden test, and review missed it. The same bug class appeared in 2 of 3 runs of another of our studies. [paraphrase]

The goal is to improve our process so that this gap closes, without increasing wall-clock time massively or regressing elsewhere. [paraphrase]

## Architecture & Data Models

This changes guidance only. Every change is a sentence of guidance in the stage text agents already read on a fix:
- the defect route's base-and-head proof step;
- the shared working rules' Tests, Attended and Handoff guidance;
- the deferred-work guidance;
- the work stage's commit step. [inferred]

Generated mirrors for other hosts follow from the canonical text through the existing sync. No flowctl verb, field, check, receipt key or gating stop is added. [inferred]

## Edge Cases & Constraints

- **Bisect hygiene.** A test-only commit is red in the history. It stays on the local branch, and the usual squash merge removes it from the base branch. A repository whose instructions forbid red commits keeps its rule, and the hand-back carries the base observation instead. [inferred]
- **Hooks.** A pre-commit hook that runs tests or lint can refuse a commit holding a failing test. Then test and fix go in one commit, with no `--no-verify` and no extra round. [inferred]
- **Goal runs and spec builds.** These keep their own commit policy. A defect child still orders the failing test before the fix when it commits. [inferred]
- **Wall-clock.** Every change reuses observations the run already makes: one extra local commit, a literal instead of an import, and lines restated from runs already done. No new full-suite runs, review rounds or re-runs. [inferred]

## Acceptance Criteria

- **R1:** When a fix is proven by a failing test written before it, that test fails by assertion when run, as committed, against the unchanged code. It reaches the behaviour through code that already exists, for example a literal in place of a constant the fix adds, or the existing entry point instead of a helper the fix adds. Errors: when no such test can be written, the base observation is a reproduction run on the unchanged code instead, and the hand-back says which was used. [inferred]
- **R2:** A defect fix leaves the failing test as its own commit, test files only, before the fix commit. This holds attended and unattended, on the local branch only, with no push and no extra lint or typecheck round. Errors: a hook or repository rule refuses the test-only commit → one commit holding test and fix, with the base observation carried in the hand-back; uncommitted changes the run does not own stay out of both commits. [inferred]
- **R3:** Every reply that hands back a fix states the base and head observations, short and verbatim from runs already made: the failing assertion on base, the passing run on head, and before/after numbers when they were measured. That includes the reply after a follow-up and the note when a background review lands. The reply never points back to an earlier message for them and never re-runs anything to produce them. Errors: no error surface beyond an observation that was not made, which reads `not run: <reason>`. [inferred]
- **R4:** When a report names more than one symptom or surface, each gets its own base and head observation, by test or by driving that surface. Errors: a symptom that does not reproduce on base is recorded as not reproduced, and the fix does not claim it. [inferred]
- **R5:** When a change throttles, coalesces or defers persisted writes, the value a caller reads in the same process stays exact; only the write is deferred. A test reads the live value straight after the event. Errors: no error surface beyond the existing check that guarantees hold when the process stops before the deferred work runs. [inferred]
- **R6:** A pre-registered A/B compares 9.6.0 against 9.6.0 with this change, with 6 runs per arm on each of the two bug cases, on each host where the gap was measured (Claude Code and Cursor). It passes when the changed arm meets all of these: [inferred]
  - judge verification mean of at least 3.75 of 4 on each case;
  - judge total not below 9.6.0's on any case;
  - the grader sees an assertion red, and a test-only commit before the fix, in at least 5 of 6 defect runs per case;
  - median time to first hand-back no more than 10% (and no more than 60 s) above 9.6.0 on each case;
  - hidden-test pass rate not lower than 9.6.0's.

  A regression set (a small feature and a large feature, 3 runs each against 9.6.0) stays within 9.6.0's ranges on judge, hidden tests and wall time. Errors: a harness fault discards and re-runs the draw, logged.

## Boundaries

- No change to the eval harness is part of this spec; re-scoring stored runs is a separate decision. [inferred]
- No push or pull request in attended runs; R2's commit is local. [inferred]
- No change to feature routes beyond the shared Tests sentence R1 adds. [inferred]
- No new structure: no fields, labels, verbs, checks or stops (repo agent-first rule). [inferred]

## Decision Context

Changing only how the grader detects a red would correct the score but leave the real gaps. A reviewer still could not replay the red, the last reply would still lack the evidence, and the second symptom would still go untested. So the process closes the gap against a strict reader. [inferred]

Before/after numbers on every route were rejected. They already exist for the measured-slowness route, and the verification score tracked the replayable red, not the numbers. [inferred]

An earlier hand-back-evidence experiment (October) was judged when the grader read only the last message. R3 is re-measured here with the full hand-back as input. [inferred]

R2 changes the attended "commit only when review needs it" rule for defect fixes. It is in scope because the request is to close the gap, and the commit is local and cheap. [inferred]

## Strategy Alignment

- The Autonomous mode track holds "evidence over narration" as invariant quality discipline; R1, R3 and R4 make a fix's proof replayable and visible in the reply. [strategy:Autonomous mode]
