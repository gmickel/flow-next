# Feature map across flow's live-app routes

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 15% [user], 50% [paraphrase], 35% [inferred] -->

fn-261 makes flow's bug intake resolve a report to a mapped feature and reproduce along the map's route. The same navigation cost appears wherever flow touches a running app: capturing a performance baseline on a real surface, QA, the defect route's live proof on base and head, and the evidence a PR carries. Today QA and the drive skill read the map, each re-selecting the feature from scratch; the performance-baseline route has no map use at all; and nothing passes a resolved feature from one stage to the next, so every stage re-derives where it is going.

This spec spreads map use to every flow route that drives a running app, makes it cheap, and carries the resolution forward so it is paid once per run. The study in this conversation measured the effect that justifies it and its limits: with a strong model the map roughly halved turns on locate-heavy work and cut median wall time from 17 to 12 seconds, while token cost per run stayed flat, and it added turns where it prescribed extra verification. So the target is wall-clock and turns, reading the map must be cheap, and each route must earn its place by measurement.

Target user: anyone whose repository has a feature map and whose flow runs touch the live app.

## Architecture & Data Models
<!-- scope: technical -->

- **Which routes.** Routes that drive a running app: the measured-slowness route's live baseline and post-change measurement, QA, the defect route's live proof on base and head, and the PR evidence of a live check. Routes with no running app (how and why questions, refactors, capture, plan, refine) do not read the map. [paraphrase]
- **Cheap loading.** A reader first checks the map exists, then reads only the index, then reads only the one matched feature file (or the few candidates when the match is ambiguous). No route reads the whole map. [paraphrase]
- **One resolution, carried forward.** The first stage in a run that resolves a report or target to a mapped feature records it as a resolved-feature record: surface, sub-feature ID, feature file, and the file's last-proven line (from the "feature map stays current" spec). Later stages in the same run read the record instead of re-selecting. This is the same carrier fn-261 introduces for bug intake; this spec makes it the shared carrier every route reads and writes, and the PR briefing shows it. [paraphrase]
- **Drift reporting** follows the "feature map stays current" spec: any reader that finds a mapped route no longer matches files the existing drift note. [paraphrase]
- **Per-route measurement.** Each route's map use ships with a measurement against the same route without the map on a fixture app, in the maintainer's evaluation setup: turns and wall time to the route's goal state, success rate no lower. A route whose measurement shows no gain drops its map use rather than keeping it on faith. [paraphrase]

### Worked example

A user reports that the checkout page got slow. Flow routes it to the measured-slowness route. The baseline step checks the map, reads the index, matches "checkout page" to the checkout feature, reads only that file, and follows its route to the page to capture the baseline. It writes the resolved-feature record (surface web, sub-feature `checkout.review`, the file, last proven eight days ago). After the fix, the post-change measurement reads the record and goes straight to the page without touching the index. When QA runs on the same spec it reads the same record, drives the checkout flow, and finds the "Place order" button renamed; it files a drift note and continues on live discovery for that one step. The PR shows the resolved feature, the baseline and post-change numbers, and the drift note.

## Edge Cases & Constraints
<!-- scope: technical -->

- No map: every route behaves as today after one existence check.
- No match: the route falls back to live discovery and the record says `unmapped`; later stages do not retry the match.
- Ambiguous match: the candidates are read and tried in order of specificity; the record names the one used.
- A record from an earlier run is never reused; the carrier lives for one run.
- A route that cannot start the app does not read the map for navigation.
- Measurement runs in the evaluation repository, not in users' repositories; flowctl records no turn counts and gains no telemetry.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The measured-slowness route's live baseline and post-change measurement, QA, the defect route's live proof, and the PR's live-check evidence each resolve their target through the map when one exists, reading only the index and the matched feature file. Errors: no map → today's behaviour after one existence check; no match → live discovery recorded as `unmapped`; ambiguous → candidates read and tried in order of specificity. [paraphrase]
- **R2:** The first stage in a run to resolve a target writes a resolved-feature record (surface, sub-feature ID, feature file, last-proven line or none), and every later stage in the same run reads it instead of re-selecting; the record is the same carrier fn-261 uses. Errors: a record from another run is ignored. [paraphrase]
- **R3:** The PR briefing shows the resolved feature (or `unmapped`) for any live check it reports. No error surface beyond R2's `unmapped`. [inferred]
- **R4:** Routes without a running app (questions, refactors, capture, plan, refine) do not read the map. No error surface. [paraphrase]
- **R5:** Each route's map use is measured before it ships: a pre-registered comparison on a fixture app, same route with and without the map, reports turns and wall time to the route's goal with success no lower; a route without a gain ships without map use, and the result is published either way. [paraphrase]
- **R6:** The flow-next.dev route pages and the feature-map page describe which routes read the map and what the resolved-feature record carries. No error surface. [inferred]

## Boundaries
<!-- scope: business -->

- No route reads the whole map. [paraphrase]
- No token or turn telemetry is added to flowctl; measurement lives in the evaluation setup. [inferred]
- The map stays navigation only; specs and reports stay the intent, and live evidence stays the proof. [inferred]
- Keeping the map current is the "feature map stays current" spec's job, and bug intake is fn-261's; this spec only adds the other routes and the shared carrier. [paraphrase]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer wants the feature map in most routes ("we would add the features thing into most routes going forward in hope of more efficient token usage and wall-clock") and flow as powerful as possible ("we want this to be as powerful as possible"). [user] The study showed the gain is wall-clock and turns rather than tokens, so the design keeps reading cheap and makes each route prove its gain. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: the feature map stays current, feature-map-aware bug intake (fn-261), a hardened defect route, the hill-climb loop, answering questions by experiment, sharper handovers, a read-only PR status answer, diagnosing a captured profile, and resume and review hygiene. It depends on "feature map stays current" and on fn-261.

## Strategy Alignment

Serves the approach line that flow is the one dial on the default path: the routes it chooses get faster when the map exists. Serves **Self-improving through normal work**: the map becomes a shared asset every live route reads and reports drift against.

## Strategy Conflicts

None found.
