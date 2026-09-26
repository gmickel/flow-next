# Resume and review hygiene

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 45% [paraphrase], 45% [inferred] -->

Four small gaps each cost a session some time or a reviewer some trust. Work can pause safely only at a wave boundary, only on its wave route, and writes its resume note to a temporary directory that other sessions share and that can fill up. The why-scout lists sources it could not read but omits sources it read and found empty, and it does not consult error-tracking, observability or documentation tools even when they are configured. resolve-pr triages review-bot comments from scratch every round, although the same bots raise the same kinds of valid findings and the same kinds of noise. And the no-plan route gives the owner a broad licence to fan out, with no guidance to prove one unit before fanning out a batch of similar ones.

This spec closes all four. None changes a gate or a cap.

Target user: maintainers who pause and resume long runs, ask why the code is shaped the way it is, resolve review feedback, or hand work a batch of similar items.

## Architecture & Data Models
<!-- scope: technical -->

- **(a) Safe pause anywhere.** The existing pause (explicit request or compaction signal only, never self-granted) extends to the rolling route and to a stop in the middle of a task. It commits only the run's own paths as a work-in-progress commit, names any pre-existing uncommitted edits without committing them, and writes the resume note to the flow directory's gitignored scratch area instead of the shared temporary directory, so it survives other sessions. Resumption reads the note and the committed state, never the transcript, and re-verifies any pass or fail claim the note makes. [paraphrase]
- **(b) why-scout sources.** The why-scout also consults error-tracking, observability and documentation sources when a connected tool for them is already available in its tool list; it never configures, installs or authenticates anything. Its answer ends with one line listing every source it checked, including the ones that returned nothing, alongside the existing list of sources it could not read. It stays read-only and within its token budget. [paraphrase]
- **(c) Review-bot patterns.** When memory is enabled, resolve-pr records recurring review-bot comment patterns as memory entries with a stable title identity (bot, pattern, verdict: usually valid or usually noise, with an example and the reason), updating rather than duplicating them. Later triage reads them as priors for a faster first pass; every comment is still judged on its merits, and comment bodies stay untrusted input. [paraphrase]
- **(d) Pilot before batch.** The no-plan route's guidance to the owner adds: when the work is a batch of similar units, prove one unit end to end before fanning out the rest. It is guidance within the owner's licence, not a prohibition; the owner still chooses the shape. [paraphrase]

### Worked example

A long rolling run is halfway through a task when the user says "pause, I need to switch machines". Work commits the task's changed files as a work-in-progress commit, leaves an unrelated edited file uncommitted and names it, and writes the resume note into the flow scratch area: the task, what is done, what is next, and which checks passed at which commit. On the other machine, work reads the note, re-runs the checks it claims passed, and continues.

Two weeks of PRs later, resolve-pr has seen the same bot flag "possible null dereference" on guarded optional chains nine times, all noise, and "missing await" four times, all valid. Its memory now says so, with examples. On the next PR it triages both kinds in one pass and still reads each comment before dismissing it.

## Edge Cases & Constraints
<!-- scope: technical -->

- A pause never happens without an explicit request or a compaction signal.
- Memory disabled: resolve-pr neither reads nor writes bot patterns.
- Land's promise that it keeps no files between runs is about its own run files; memory is a separate opt-in store, and the land and resolve-pr docs say so.
- why-scout omits empty sections as today except for the single sources-checked line.
- The generated agent mirrors and the pinned tests change together with the prose.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** On an explicit pause request or compaction signal, work pauses safely on both the wave and rolling routes and mid-task, committing only its own paths as a work-in-progress commit, naming pre-existing uncommitted edits, and writing the resume note to the flow scratch area; resumption re-verifies the note's claims. Errors: no explicit signal → no pause; a commit that would include foreign paths → those paths are left uncommitted and named. [paraphrase]
- **R2:** why-scout consults configured error-tracking, observability and documentation tools when they are available to it, never configuring or authenticating anything, and ends with one line listing every source checked, including empty ones. Errors: a tool that fails → listed under could-not-read. [paraphrase]
- **R3:** With memory enabled, resolve-pr records and updates recurring review-bot patterns with a stable title identity and reads them as triage priors, still judging every comment on its merits. Errors: memory disabled → no read or write; a pattern entry that contradicts a comment's evidence → the evidence wins. [paraphrase]
- **R4:** The no-plan route's owner guidance recommends proving one unit before fanning out a batch of similar units, without prescribing the shape or forbidding anything. No error surface. [paraphrase]
- **R5:** The work, resolve-pr, land and planning-scouts pages on flow-next.dev describe the four changes. No error surface. [inferred]

## Boundaries
<!-- scope: business -->

- No self-granted pauses. [inferred]
- No new dependency and no configuration of external tools. [inferred]
- No change to review caps, triage filters' existing rules, or the owner's delegation licence. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer asked for every improvement from this review, including the lower-priority ones, to be captured ("so all of the above i want captured and the make sure everything is excellent"). [user] Each item is small and removes a recurring source of lost time or unfounded trust. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: the feature map stays current, feature-map-aware bug intake (fn-261), the feature map across live-app routes, a hardened defect route, the hill-climb loop, answering questions by experiment, sharper handovers, a read-only PR status answer, and diagnosing a captured profile. It stands alone.

## Strategy Alignment

Serves **Self-improving through normal work**: review-bot patterns accrete from resolve-pr runs and are read back without a separate ceremony.

## Strategy Conflicts

None found.
