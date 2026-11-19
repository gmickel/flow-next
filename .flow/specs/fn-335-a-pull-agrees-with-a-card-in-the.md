# A pull agrees with a card in the configured ready state

## Goal & Context

<!-- Source: 0% user / 80% [paraphrase] / 20% [inferred] -->

GitHub issue #627. A Linear team can put its ready column among the started states: a card moved there is admitted for work. When an unstarted spec's card sits in that configured `tracker.readyState`, a pull projects readiness, merges the body, and then fails its status step with `status conflict (unmapped): flow='backlog' tracker='in_progress'`. The command ends unsuccessful with exit 10, so a caller reads the pull as failed although the readiness flag it exists to project has landed.

Configuration cannot fix it. Mapping the ready state into the `todo` slot makes it read as `todo`, and then every status push to `todo` moves the card into the ready state, so flow-next would admit specs on its own.

The unattended failure this prevents: a `flow --auto` run or a scheduled pull treats an admitted card as a failed sync and stops or retries, on the one board move that is a person's consent to start.

Part of the reported table is already fixed on main: `backlog` against `todo` agrees either way round. What remains is an unstarted spec against a card the provider reads as in progress because the ready state is a started-type state.

## Architecture & Data Models

- The status decision learns one fact it does not have today: whether the card's current state is the configured ready state. The comparison already exists for readiness projection, per provider and case-insensitive; the status step reuses it. [paraphrase]
- When that fact holds and the spec has not started, the status step treats the pair as agreeing and writes nothing to the tracker, like the existing agreement between `todo` and `backlog`. [paraphrase]
- Nothing is stored. No config key is added. [inferred]

## Edge Cases & Constraints

- The agreement applies only while the card is in the configured ready state. A card in any other started state against an unstarted spec stays a conflict. [paraphrase]
- A spec that has started (in progress, in review, done) keeps today's rules whatever the card's state. [paraphrase]
- No status push moves a card into or out of the ready state as a result of this change. Admission stays a person's board act. [inferred]

## Acceptance Criteria

- **R1:** A pull of a spec that has not started (no tasks, or only todo tasks) whose card is in the configured `tracker.readyState` ends successful: readiness is projected, the status step is a no-op at the tracker's slot, and no status write goes to the tracker. This holds when the ready state is a backlog-type, unstarted-type or started-type state. [paraphrase]
  Errors: `tracker.readyState` unset → today's behaviour, unchanged; the card in a started state that is not the ready state → still `status conflict (unmapped)`; a request for a status other than backlog or todo → today's rules.
- **R2:** A started spec against a card in the ready state, and every pairing where the card is not in the ready state, decides exactly as before. [paraphrase]
  Errors: no error surface beyond R1.
- **R3:** The rule holds for every tracker provider that supports `tracker.readyState`, not Linear alone. [inferred]
  Errors: a provider with no ready-state concept is unaffected.
- **R4:** The failing rows of the issue's table are reproduced on current main before the fix and covered by a regression test after it, at the same entry point a `tracker sync --op pull` goes through. [inferred]
  Errors: a row that no longer reproduces on current main is recorded as already fixed, not re-fixed.
- **R5:** The changelog entry credits the reporter of #627. [inferred]
  Errors: no error surface.

## Boundaries

- No new mapping slot or config key for the ready state. [inferred]
- No change to which side wins a real status disagreement. [inferred]
- No change to readiness projection itself. [inferred]

## Decision Context

The reporter's sketch (agreement only when the card is in the ready state, about a dozen lines) is taken as the approach: it is the narrowest rule that ends the false failure, and it reuses a comparison flowctl already makes. Reordering the pull so status runs before readiness was not taken; it would hide the conflict's side effect and keep the false failure. [inferred]
