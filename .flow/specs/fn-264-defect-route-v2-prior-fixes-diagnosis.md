# Defect route v2: prior fixes, diagnosis, bisect, base vs head

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 50% [paraphrase], 40% [inferred] -->

When `/flow-next:flow` is handed a reported defect, its route is one line: reproduce first, make the failing test the requirement, then work and review. How the reproduction is obtained, what is checked before a fix is written, and how the fix is proven are left to the agent. In practice that invites three expensive mistakes: writing a second fix for a bug someone already fixed or is fixing; designing a fix on a guessed cause; and "proving" a fix with a test that would have passed before the change too.

This spec turns the defect route into a disciplined sequence. Before anything is written, check whether the work already exists. Before the fix is designed, establish the cause with runtime evidence, and bisect when a known-good revision exists. After the fix, show the symptom on the base and its absence on the head, on the live app when there is one. The maintainer asked for this set of improvements to make flow as capable as possible, with each piece done properly.

Target user: anyone who hands flow a bug report, console output, a screenshot or a failing behaviour, attended or through a defect-shaped ready spec under `flow --auto`.

## Architecture & Data Models
<!-- scope: technical -->

The defect route becomes four ordered steps, all host judgment, with flowctl providing only the facts it already can (git, PR and memory lookups):

1. **Prior-fix check (before any fix is authored).** Look for existing work on the same defect: open pull requests and branches that touch the affected area, recent commits and reverts in that area, the bug track in memory for the same symptom or root cause, and tracker issues that describe the same symptom. Outcomes: an existing fix artifact is found → verify that fix against the reproduction instead of writing a competing one, and report the result; a human visibly owns an in-flight fix → stop and hand back (attended: say so; unattended: `NEEDS_HUMAN`); an earlier attempt was reverted or recorded as failed → its reason becomes a known-refuted hypothesis for step 2; nothing found → continue. [paraphrase]
2. **Reproduce, then diagnose before designing the fix.** The symptom must reproduce, and reproduce a second time, before diagnosis starts. Diagnosis lists candidate causes, then eliminates them one at a time with runtime evidence (instrumentation, logs, a narrowed input), taking the check that cuts the most remaining possibilities first. The fix is designed only after the surviving mechanism is confirmed by evidence, not by reading source. When the reproduction is flaky, tighten the conditions or instrument until it fires reliably; a symptom that will not reproduce is reported as such, never "fixed" blind. [paraphrase]
3. **Bisect when a known-good revision exists.** When the report or history names a revision where the behaviour was correct, run a bisection driven by the reproduction (a script that exits zero on good and non-zero on bad) to find the introducing change. The introducing change and its intent (from its commit and PR) feed the fix design. [paraphrase]
4. **Prove on base and head.** The failing reproduction is committed before the fix (today this is preferred; on this route it becomes the rule when the reproduction is a cheap test). The symptom must be shown present on the base revision and absent on the head, through the same reproduction. When the defect is on a live surface, the check runs on the live app (through the drive skill, and through the feature map when fn-261 is in place). A reproduction that passes on base is not a reproduction of this defect. [paraphrase]

The evidence of each step (what the prior-fix check found, the eliminated and surviving hypotheses, the bisected commit, the base and head observations) travels with the task's done evidence and appears in the PR briefing, so a reviewer sees the cause and the proof, not only the diff. [inferred]

Placement respects the routing reference set: the defect row's route cell names the four steps; the step detail lives with work and the worker rather than as a new routing reference, because the routing reference folder is a fixed set. [inferred]

### Worked example

A user pastes: "Export to CSV drops the last row since last week." Flow routes a defect with no reproduction yet.

Prior-fix check: no open PR touches the exporter; the bug track has no matching entry; but a commit from four days ago is titled "perf: stream CSV rows" and there is a reverted attempt from two days ago, "fix: flush csv writer", reverted because it doubled the header. That revert's reason is recorded as a refuted hypothesis (flushing alone is not it).

Reproduce: a 3-row fixture exports 2 rows, twice. Diagnose: candidates are an off-by-one in the row loop, the writer not flushed at close, and a generator exhausted early by a length check. Instrumenting the loop shows all three rows are yielded; logging the writer shows the third row is written to the buffer; the file on disk has two rows. Flushing was refuted earlier, so the surviving mechanism is the file handle closing before the buffered writer. Confirmed by logging close order.

Bisect: the report says it worked last week, so the reproduction script drives a bisection from that week's tag and names the "stream CSV rows" commit, which moved the file handle into a context manager that closes before the writer drains.

Prove: the failing test (3 rows in, 3 rows out) is committed first and fails on base. The fix closes the writer inside the handle's context. On head the test passes and the live export in the app downloads 3 rows. The PR shows the eliminated causes, the bisected commit, and the base and head observations.

## Edge Cases & Constraints
<!-- scope: technical -->

- No git history to bisect (a new repository, a squashed import) or no known-good revision: skip step 3 and say so.
- A reproduction that is expensive or needs the live app for every run: bisection uses the cheapest reliable reproduction; if none is cheap enough, skip bisection and record why.
- Prior-fix lookups need network access for pull requests and tracker issues: when unavailable, record which sources were checked and which were not; the route continues on local evidence.
- Several open PRs plausibly touch the area: list them; attended, ask which applies; unattended, `NEEDS_HUMAN` with the list.
- A defect in a library with no live surface: base and head proof is the test alone.
- `flow --auto` meets only defect-shaped ready specs (it never takes raw intent), never asks a question, and turns every ambiguity above into `NEEDS_HUMAN`.
- Hypotheses, diagnosis and the fix design stay host judgment; flowctl gains no heuristics, word lists or model calls for them.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Before any fix is authored on the defect route, the prior-fix check runs over open PRs and branches touching the area, recent commits and reverts in the area, the memory bug track, and tracker issues, and its findings are recorded. Errors: an existing fix found → the route verifies it instead of authoring a new fix; a human-owned in-flight fix → attended hand-back or unattended `NEEDS_HUMAN`; an unreachable source → recorded as unchecked, route continues. [paraphrase]
- **R2:** A reverted or recorded-failed earlier attempt found by the prior-fix check enters diagnosis as a refuted hypothesis with its reason, and is not retried unchanged. No error surface beyond R1. [inferred]
- **R3:** The symptom is reproduced twice before diagnosis; diagnosis records candidate causes, the evidence that eliminated each, and the evidence confirming the surviving mechanism; the fix is designed only after confirmation. Errors: a symptom that does not reproduce → reported as not reproduced, with what was tried, and no fix is shipped for it. [paraphrase]
- **R4:** When a known-good revision exists, a bisection driven by the reproduction identifies the introducing change, and that change is cited in the diagnosis. Errors: no known-good revision or no bisectable history → step skipped with the reason recorded; a reproduction too costly to bisect → skipped with the reason recorded. [paraphrase]
- **R5:** The fix is proven by the same reproduction failing on the base revision and passing on the head; on a live surface the check runs on the live app. Errors: the reproduction passes on base → the route reports that the reproduction does not capture the defect and does not claim the fix; the live app cannot be started → the test-level proof stands and the live check is recorded as not run. [paraphrase]
- **R6:** When the reproduction is a cheap test, it is committed before the fix on this route. No error surface beyond the existing worker rule for expensive or integration-heavy reproductions, which stay preferred rather than required. [inferred]
- **R7:** The prior-fix findings, the diagnosis record, the bisected change (when found) and the base and head observations appear in the task's done evidence and in the PR briefing. Errors: any missing element renders as not done rather than being omitted. [inferred]
- **R8:** The defect row of the routing table, the judge's defect wording, the pipeline-variations guide and the flow-next.dev pages that describe bug fixing all describe the four steps consistently; the stale mention of a separate diagnose skill in the team guide is removed. No error surface beyond the routing pin tests passing after the edit. [inferred]

## Boundaries
<!-- scope: business -->

- No new routing reference file; the routing reference set stays fixed. [inferred]
- No separate diagnose skill; the discipline lives in the defect route. [inferred]
- flowctl gains no hypothesis heuristics or model calls; it only supplies git, PR, memory and tracker facts it can already read. [inferred]
- Feature-map navigation for the reproduction is fn-261's scope; this spec uses it when present and does not change it. [paraphrase]
- `flow --auto` still never accepts raw intent. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer wants flow to be as powerful as possible and asked for every one of these improvements to be captured and done well ("we want this to be as powerful as possible", "definitely do all of this", "make sure everything is excellent"). [user] The defect route is the most common way real work enters flow, and today it is the least specified. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: keeping the feature map current, feature-map-aware bug intake (fn-261), the feature map across live-app routes, the hill-climb loop, answering questions by experiment, sharper handovers, a read-only PR status answer, diagnosing a captured profile, and resume and review hygiene. It depends on fn-261 because both change the defect route's reproduction step; landing fn-261 first avoids two conflicting edits of the same step.

## Strategy Alignment

Serves the approach line that flow reads whatever the user has and routes it through one shared routing reference; this makes the most common route do its job fully. Serves **Self-improving through normal work**: refuted hypotheses and root causes flow into the bug track, and the prior-fix check reads them back.

## Strategy Conflicts

None found.
