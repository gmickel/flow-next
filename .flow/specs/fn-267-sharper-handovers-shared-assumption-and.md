# Sharper handovers: shared assumption and safety fact

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 45% [paraphrase], 45% [inferred] -->

Two handovers carry most of the weight when an agent hands work back to a person: the stop when repeated attempts fail, and the PR briefing a reviewer reads first. Both could say more with the same effort.

When two attempts fail the same gate (work's two-strike escalation, land's bounded CI repair, flow --auto's strike ledger, resolve-pr's cycle budget), the handover says what failed but not why both attempts failed. Often they failed for the same reason: both assumed something that is not true. Naming that assumption, and one alternative worth trying, turns a dead stop into a useful next step.

The PR briefing has a free-text blast-radius field. It rarely says the single thing a reviewer most needs: which one fact the change is safe because of, and how far that fact was actually proven. A change is safe because "only the export path calls this function" or "the new column is nullable"; the reviewer should see that fact and whether it was just stated, pointed at in the code, walked through, run, or reproduced in the app.

Target user: the human who receives a stop, and the reviewer who opens the PR.

## Architecture & Data Models
<!-- scope: technical -->

- **Shared assumption in escalations.** The worker's blocked-escalation format gains two lines: the assumption the failed attempts shared, and one alternative worth trying next. Work's wave and rolling routes relay them as they relay the rest of the escalation. Land's blocked reason, flow --auto's strike reason and resolve-pr's cycle-budget stop carry the same pair in their reason text. It is host judgment written in prose. No counter, cap, reset rule or refund changes, and no trend heuristic is added. When the attempts did not share an assumption, the line says so. [paraphrase]
- **Reason-line shape.** Terminal verdict lines stay one parseable line; the strike reason keeps its recovery clause last. [inferred]
- **Safety fact in the PR briefing.** The briefing's authored fields gain one additive field: the fact the change is safe because of, and its proof level, one of stated, pointed at the code, walked through, ran it, reproduced in the app, or unproven. The field is optional, existing briefings stay valid, the schema version stays the same, and unknown-field rejection stays. The briefing renders it inside the blast-radius section. The proof levels align with the existing proof outcomes (a fact proven by running it is backed by a passing proof). [paraphrase]
- **Consumers.** The field is additive and generic, so downstream readers of the briefing artefact keep working; none is named or specialised for. [inferred]

### Worked example

Work's rolling route fails the same task twice. Attempt one added a retry around a flaky upload; attempt two raised the timeout. Both still fail the integration gate. The escalation now reads, beside the category and summary: "Shared assumption: the upload fails because the network is slow. Alternative: the test server rejects the second chunk (both runs log a 413 on chunk 2); check the server's body-size limit." A person reads one line and knows where to look.

The PR for a schema change shows under blast radius: "Safe because: the new `archived_at` column is nullable and no existing query filters on it. Proof: ran it (the migration applied to a copy of production-shaped data and the full query suite passed)." Another PR shows "Safe because: only the CSV exporter calls `format_row`. Proof: pointed at the code (single call site)", which tells the reviewer exactly how much weight that claim can bear.

## Edge Cases & Constraints
<!-- scope: technical -->

- The two attempts failed for unrelated reasons: the assumption line states that and the alternative line may be empty.
- Review-round caps, transport-failure caps, the not-retryable terminal and the strike counts are untouched.
- An author cannot name a single safety fact: the field records `unproven` with the reason, rather than inventing one.
- Older briefings without the field render exactly as before.
- The generated agent mirrors and the pinned briefing tests change together with the prose.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A worker escalation after repeated failure includes the shared assumption of the failed attempts and one alternative, and both work routes relay them. Errors: no shared assumption → the line says so and the alternative may be empty. [paraphrase]
- **R2:** Land's blocked reason, flow --auto's strike reason and resolve-pr's cycle-budget stop include the same assumption-and-alternative pair while staying one parseable line, with the strike reason's recovery clause still last. No error surface beyond the existing verdict grammar tests passing. [paraphrase]
- **R3:** No review-round cap, transport-failure cap, strike count, reset rule or refund changes, and no trend heuristic is introduced. No error surface. [inferred]
- **R4:** The PR briefing accepts an optional safety-fact field with a proof level from stated, pointed at the code, walked through, ran it, reproduced in the app, or unproven, renders it under blast radius, and keeps older briefings valid with the same schema version and unknown-field rejection. Errors: a proof level outside the list → rejected by the validator. [paraphrase]
- **R5:** make-pr fills the safety fact on every briefing it authors, choosing the proof level from the evidence it has, and writes unproven with a reason when it has none. No error surface beyond R4. [paraphrase]
- **R6:** The make-pr, pilot, land, resolve-pr and troubleshooting pages on flow-next.dev and the briefing reference doc describe both additions with examples like the ones in this spec. No error surface. [inferred]

## Boundaries
<!-- scope: business -->

- Prose only for the assumption line; no new flowctl mechanism decides it. [inferred]
- No change to review convergence rules or caps. [inferred]
- No briefing form flag or config key; one briefing form. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer asked for every improvement from this review to be captured and done well ("so all of the above i want captured and the make sure everything is excellent"). [user] Better handovers cost the agent one sentence each and save the human the investigation. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: the feature map stays current, feature-map-aware bug intake (fn-261), the feature map across live-app routes, a hardened defect route, the hill-climb loop, answering questions by experiment, a read-only PR status answer, diagnosing a captured profile, and resume and review hygiene. It stands alone.

## Strategy Alignment

Serves the approach line of reviewable handover objects between idea and merge: both changes make an existing handover object carry the reasoning a human needs.

## Strategy Conflicts

None found.
