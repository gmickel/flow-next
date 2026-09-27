# Feature map across flow's live-app routes

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 15% [user], 50% [paraphrase], 35% [inferred] -->

fn-261 makes flow's bug intake resolve a report to a mapped feature and reproduce along the map's route. The same navigation cost appears wherever flow touches a running app: capturing a performance baseline on a real surface, QA, the defect route's live proof on base and head, and the evidence a PR carries. Today QA and the drive skill read the map, each re-selecting the feature from scratch; the performance-baseline route has no map use at all; and nothing passes a resolved feature from one stage to the next, so every stage re-derives where it is going.

This spec spreads map use to every flow route that drives a running app, makes it cheap, and carries the resolution forward so it is paid once per run. The feature-map study in the maintainer's evaluation repository (agent-evals, branch `study/feature-map-2026-09`, `studies/feature-map-2026-09/REPORT-v2.md`, which also holds the reusable fixture harness: isolated T3 Code v0.0.42 instances and a live-state scorer) measured the effect that justifies it and its limits: with a strong model the map roughly halved turns on locate-heavy work and cut median wall time from 17 to 12 seconds, while token cost per run stayed flat, and it added turns where it prescribed extra verification. So the target is wall-clock and turns, reading the map must be cheap, and each route must earn its place by measurement.

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

**Resolved details for implementers.**

- Scope of the resolved-feature record is the spec, not a session: QA, work and make-pr often run as separate invocations, so the record lives in the spec's task evidence and is valid until the spec's PR merges.
- Measurement (R5) runs in the maintainer's evaluation repository (agent-evals, following its METHODOLOGY.md and reusing the feature-map study's fixture harness), one preregistered comparison per route, sonnet-class model held constant, about 20 to 40 draws per route; the implementing run proposes each study and the maintainer approves the spend.
- Shipping order inside this spec: the carrier and the measurement studies first, then map use enabled route by route as each study reports a gain; the PR states which routes shipped with map use and why.
- PR briefing: this spec adds no briefing schema field (only fn-267 does); its content goes into the existing authored prose fields and proof cells within their current limits, with the full record in task evidence.
- fn-260's studies have not drawn baselines yet, so this spec lands first; its always-reached text goes where the behaviour lives, and rarely reached text goes into the new reference file named here, which fn-260's studies then measure as the current state. New drive text goes into drive's existing references.
- Docs changes land in the flow-next.dev site repository (content under `src/content/docs/`) as a separate change in the same work run, per the project rule that flow-next.dev is the canonical user documentation.

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

- **R1:** When a repo has a feature map, every stage that is about to drive the running app on these routes (the measured-slowness route's live baseline and post-change measurement, QA, the defect route's live proof on base and head, and the PR's live-check evidence) reads the map index and the one matched feature file before driving, whether or not the target names its place: the map carries both navigation and driving notes (controls that misbehave, state that the accessibility tree misreports), and the notes pay off even on a named page. No stage reads the whole map. Errors: no map → today's behaviour after one existence check; no match → live discovery recorded as `unmapped`; ambiguous → candidates read and tried in order of specificity. fn-261's bug-intake gate is unchanged. [user]
- **R2:** The first stage on a spec to resolve a target writes the resolved-feature record fn-261 defines (the `resolved_feature` object in task evidence), and every later stage on the same spec reads the newest record instead of re-selecting. Errors: a record from another spec is never read; a record whose feature file changed since it was written is re-resolved. [paraphrase]
- **R3:** The PR briefing shows the resolved feature (or `unmapped`) for any live check it reports. No error surface beyond R2's `unmapped`. [inferred]
- **R4:** Routes without a running app (questions, refactors, capture, plan, refine) do not read the map. No error surface. [paraphrase]
- **R5:** The map use in R1 rests on the lean pre-registered study `live-routes-map-2026-09` in agent-evals (66 draws over two passes, one model): on targets the input did not locate, the map cut turns 38-47% and wall time 31-53% with success no lower; on named targets, reading the index plus one file always cost 0-3 turns and once saved 14 by warning about a misreporting control, while fn-261's gate withheld that note; the gate-versus-always comparison was pre-registered as inconclusive and the maintainer chose always-read on the evidence. The defect route's base-and-head proof was not measurable on the single-build fixture and follows the same live-drive rule. The study lives in agent-evals; public docs state only which routes read the map. [user]
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

Related open work: fn-260 R5 studies trimming the drive skill's main file to save tokens. New drive text from this spec goes into drive's existing references, not its always-loaded file.

Delivery order: 4 of 10 in this set (fn-262 → fn-261 → fn-264 → fn-263 → fn-265 → fn-266 → fn-267 → fn-268 → fn-269 → fn-270, which is the order `flow --auto` picks them once ready); needs fn-262, fn-261 and fn-264; extends fn-261's resolved-feature record. Hard dependencies are recorded on the spec, so `flowctl spec chain` refuses a spec whose dependency is not done. Route: direct, `/flow-next:work fn-263-feature-map-across-flows-live-app-routes --no-plan`.

### Outcome and scope decision (2026-09-27)

Instead of four 20-40-draw studies, the maintainer asked for a lean sequential study run until a call could be made (agent-evals `study/live-routes-map-2026-09`, $23.55 total). Pass 1 (42 draws, gated map vs no map) found the not-located gain on all three measurable routes and a located-cell cost on the PR check that did not replicate once text-entry guidance was equalised. Pass 2 (24 draws) added an always-read arm: worse than the gate on one named task (+3 turns), better on one (-14, via the map's driving notes) and equal on one, and slightly better on the not-located task. The pre-registered rule called gate-vs-always inconclusive; the maintainer chose always-read on the live-app routes, matching how pstack treats the map as navigation memory, and kept fn-261's intake gate until its own rerun. R1 and R5 were amended accordingly. [user]

## Strategy Alignment

Serves the approach line that flow is the one dial on the default path: the routes it chooses get faster when the map exists. Serves **Self-improving through normal work**: the map becomes a shared asset every live route reads and reports drift against.

## Strategy Conflicts

None found.
