# Read-only PR status in attended flow

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 15% [user], 45% [paraphrase], 40% [inferred] -->

Asking attended `/flow-next:flow` "is PR 470 green?" or "anything outstanding on the tracker PR?" should get a status report. Today a pull request that resolves to a spec takes the landing rules first, and attended flow offers to land it: a consent question nobody asked for. A plain question about a PR probably takes the read-only question route, which answers from the repository, history and memory and does not read the PR's checks, review threads or mergeability. No command answers "what is the state of this PR" without also preparing to act on it.

This spec adds a read-only status answer for status questions in attended flow, and leaves every unattended and landing behaviour exactly as it is.

Target user: anyone checking on a PR through flow without wanting it moved.

## Architecture & Data Models
<!-- scope: technical -->

- **Status question.** When attended flow is asked about the state of a pull request (green, outstanding, mergeable, what is blocking), it produces one read-only report: CI checks and their state, unresolved review threads and who owns them, mergeability and conflicts, the linked spec and its completion state when there is one, and what would come next. It asks nothing and offers nothing. [paraphrase]
- **Work stays work.** A spec id or a PR given as something to do ("land 470", "finish fn-12") keeps today's behaviour, including the landing offer. `--until=merge` and current explicit landing authority keep today's behaviour. [paraphrase]
- **Unattended paths untouched.** `flow --auto` and `--tick` never take a question as input and are not changed; their open-PR handling, deferral to land and verdict lines stay byte-for-byte. [paraphrase]
- **Placement.** The routing table's read-only question row names PR state as something it answers by reading the PR; the attended tail gains a no-offer branch for status questions. The status report reads PR facts directly rather than through land's dry run, which stops early for PRs without a finished spec. [paraphrase]

### Worked example

"Is 470 green?" Flow answers: "PR #470 (fn-255, unattended-run correctness fixes): 11 of 12 checks passed, `windows-tests` failed on `test_rolling_notes_pointer` (log linked); 2 review threads unresolved, both from the reviewer bot, both on the scheduler file; mergeable, no conflicts; the spec is done. Next if you want it moved: fix the Windows failure, then land." No landing question follows. If the user then says "land it", the normal landing path runs with its usual consent.

## Edge Cases & Constraints
<!-- scope: technical -->

- A PR number that does not exist or cannot be read (no network, no permission): the report says what could not be read.
- A question that mixes status and intent ("is it green, and if so merge it"): the status part is answered read-only, and the action part goes through today's consent, asked once.
- Several PRs match a loose reference: the report lists the candidates rather than guessing.
- The routing table rows and the judge's criteria stay in verbatim sync; any row edit updates the pinned judge literals and tests in the same change.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** In attended flow, a status question about a pull request produces one read-only report (checks, unresolved threads, mergeability, linked spec state, next step) and no landing offer or other question. Errors: unreadable PR → the report names what could not be read; ambiguous reference → candidates listed. [paraphrase]
- **R2:** A spec id or PR given as work, `--until=merge`, and current explicit landing authority keep today's behaviour, including the landing offer where it applies today. Errors: a mixed status-and-action request → status answered read-only, then today's consent asked once for the action. [paraphrase]
- **R3:** `flow --auto` and `--tick` behaviour, their open-PR handling, deferral to land and verdict lines are unchanged, and the existing tests that pin them pass unmodified. No error surface. [paraphrase]
- **R4:** The status report never writes state: no comments, labels, pushes, reruns, tracker updates or flow state changes. No error surface. [inferred]
- **R5:** The flow skill page and the route guide on flow-next.dev describe the status answer with an example. No error surface. [inferred]

## Boundaries
<!-- scope: business -->

- No change to unattended flow or land. [paraphrase]
- No reruns, comment replies or fixes from a status question. [inferred]
- No new command; this lives in flow. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer confirmed the scope condition directly ("will 7 : read-only pr status break our flow-next:flow --auto stuff, no right?") and wants the full set captured and excellent. [user] A status answer that does not try to move the PR makes flow safe to ask casually. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: the feature map stays current, feature-map-aware bug intake (fn-261), the feature map across live-app routes, a hardened defect route, the hill-climb loop, answering questions by experiment, sharper handovers, diagnosing a captured profile, and resume and review hygiene. It stands alone.

## Strategy Alignment

Serves the approach line that attended flow stops at the next decision that is the user's: a status question contains no decision to make.

## Strategy Conflicts

None found.
