# Opt-in spec-wins issue body at first claim and make-pr

## Goal & Context

GitHub issue #543. Some teams treat the spec file as the only record and read the tracker issue as a copy of it: nobody should edit the description on the tracker, and an edit made there should not survive. Today the bridge cannot keep the issue equal to its spec once the issue exists. [paraphrase]

- The first claim (`work.firstClaim`) moves status only and never writes the body.
- Every lifecycle body write either refuses a tracker-edited body or keeps it through the three-way merge, and unattended runs never overwrite.
- make-pr's reconcile keeps the issue prose on purpose. When the spec moved, it records the new spec and the old live body as a pair, so later pushes hit the echo fence and write nothing while the issue still shows the old text.

The unattended failure this prevents: under `flow --auto` and goal mode, a tracker-edited or stale issue body never converges on the spec, because every unattended step defers rather than overwrite. A team that wants the spec to win has no way to say so, short of its own script. [inferred]

## Architecture & Data Models

- One new tracker setting, `tracker.specWins` (boolean, default false). When it's unset or false, nothing changes anywhere. [inferred]
- The setting is a person's standing consent to overwrite the issue body with the spec. It is the only route by which an unattended step overwrites a tracker edit. [inferred]
- It changes exactly two existing steps; no new event, verb or command is added. [inferred]
  - **First claim:** besides its status move, the claim writes the rendered spec as the issue body (body only, no title or relation step).
  - **make-pr reconcile:** the final body it sends is the rendered spec instead of the tracker snapshot.
- Both steps compare the live issue body with the rendered spec, not with the recorded pair. That way, a pair recorded without a write cannot suppress the update. When the two are equal, no write is sent. [paraphrase]
- After a write, the step reads the issue back and records the pair the same way an ordinary push does, so the next comparison starts from what the tracker actually holds. [paraphrase]
- Every other event (capture, refine and plan pushes, pulls, comments) behaves exactly as today. [inferred]

## API Contracts

- `tracker.specWins: true | false`, default false. Readable through `flowctl config get tracker.specWins`. The published config schema declares it boolean, and the docs list it with the other tracker keys. flowctl treats any value other than `true` as off. [inferred]
- With `tracker.specWins: true`:
  - **First claim:** writes the body only when the live body differs from the rendered spec. Its receipt records whether the body was written, unchanged, or failed. [inferred]
  - **make-pr reconcile:** the body written equals the rendered spec, and the recorded pair equals what was written and read back. [inferred]

## Edge Cases & Constraints

- **Body write fails at the first claim** (network, permissions, rate limit): the status move still happens. The failure is reported in the claim's output and receipt, and the claim does not stop. [paraphrase]
- **Body write fails at make-pr:** reported like any reconcile failure today. The PR is still opened. [inferred]
- **Provider rewrites markdown** (Linear and Jira normalise the stored text): a normalised body can differ from the rendered spec on every compare, so each of the two events may write once per run. That's bounded at two writes per spec lifecycle and accepted. [inferred]
- **Spec not linked to an issue:** no change, as today. [inferred]
- **Setting off:** the first claim stays status-only. make-pr's reconcile still keeps the issue prose, records the same pair and sends the same API calls as 9.5.1. [inferred]

## Acceptance Criteria

- **R1:** With `tracker.specWins` unset or false, the first claim and make-pr's reconcile send the same tracker calls and record the same pair and receipt as before this change. Errors: no error surface beyond today's. [inferred]
- **R2:** With `tracker.specWins: true`, the first claim on a linked spec whose issue body was edited on the tracker writes the rendered spec as the body and moves the status. It reads the issue back and records the pair, and the issue body then equals the rendered spec. No title or relation call is sent. Errors: a failed body write still moves the status and is reported in output and receipt. [paraphrase]
- **R3:** With `tracker.specWins: true`, a first claim whose live body already equals the rendered spec sends no body update. This holds even when the recorded pair differs from the live body. [paraphrase]
- **R4:** With `tracker.specWins: true`, make-pr's reconcile ends with the issue body equal to the rendered spec, including after the spec changed during the work. The pair it records equals the written body, and a following `sync-body --direction push` with no spec change writes nothing. Errors: a failed write is reported as reconcile failures are today and does not block the PR. [paraphrase]
- **R5:** The published config schema declares `tracker.specWins` as a boolean, and the setting is documented alongside the other tracker keys. Errors: any value other than `true` reads as off; no new validation. [inferred]
- **R6:** Tests cover R1-R5 against the facade with a fake tracker for at least one CLI provider (GitHub) and one REST provider (Linear). They include the edited-body, equal-body, failed-write and setting-off cases, and the full existing tracker suites pass unchanged. [inferred]

## Boundaries

- No event before the first claim (the issue's second ask): the existing capture, refine and plan pushes already put the approved text on the issue. [inferred]
- No change to the title, relations, comments or status mapping. [inferred]
- No change to `conflictTiebreak`, `--overwrite-diverged` or any other event's behaviour. [inferred]
- No per-provider variants of the setting. [inferred]

## Decision Context

- **A boolean, not an enum or a reuse of `conflictTiebreak`.** `conflictTiebreak` only settles a contradiction inside a merge, and changing what it means would alter repos that already set it. A two-value enum would add nothing a boolean doesn't. [inferred]
- **Only two steps change.** The first claim and make-pr are the two places where an approved spec should be visible on the issue, and both already talk to the tracker. Adding a pre-claim event would be new machinery for text the capture and plan pushes already deliver. [inferred]
- **This deliberately breaks "surface diffs, never overwrite" for teams that opt in.** That rule protects people who edit on the tracker; a team that sets `specWins` has said nobody does. Default-off keeps the rule for everyone else. [inferred]

## Strategy Alignment

- Tracker determinism: the body a spec projects becomes a function of the spec, under a setting a person chose. [strategy:Tracker determinism]
