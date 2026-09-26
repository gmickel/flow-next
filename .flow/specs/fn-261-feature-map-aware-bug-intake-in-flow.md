# Feature-map-aware bug intake in /flow-next:flow

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 60% [paraphrase], 30% [inferred] -->

When `/flow-next:flow` receives a reported defect (a pasted bug report, console output, a screenshot, a description of failing behaviour), its route is "reproduce first". Today that reproduction works out from scratch how to reach the broken part of the app. When the repo has a committed feature map, that navigation already exists: the map records, from the user's point of view, what each feature is, how a user reaches it, and how an agent drives it. Flow's defect route does not read it; only QA and drive do.

This spec makes flow's bug intake use the map, as a speed and efficiency improvement. The maintainer's direction is to lean into `/flow-next:flow` as the product's strongest surface, and this is the first piece of that: capture it as is, and add further flow improvements later if they are pursued.

The evidence for the speed claim comes from a controlled study run in this conversation (`feature-map-2026-09` in the agent-evals repo, 84 draws on a real app, one model held constant). A strong model reproduced every report with or without a map. The map changed how fast it got there. On reports that name a place the agent must find, above all a screenshot with no page title, the map roughly halved the turns to reach the reported state (12.3 to 5.3 turns on the screenshot report, 15.0 to 7.3 on a vague "get this out of my list" report). It never changed whether the agent succeeded. The claim is therefore speed and efficiency, not success.

Target user: anyone who hands flow a bug report or screenshot in a repo that has run `/flow-next:features`.

## Architecture & Data Models
<!-- scope: technical -->

- Scope is the defect path of the conductor: the routing row "A reported defect (bug report, console dump, failing behaviour)" with a reproduction still to obtain. [paraphrase]
- Before driving the reproduction, the defect path resolves the report to one mapped feature: it reads the map's index, matches the report's wording (and the content of an attached screenshot) against the features' user-facing descriptions and sub-features, and selects by the map's existing `Surface` plus sub-feature ID contract. [paraphrase]
- The reproduction then drives through the existing drive skill, following the selected feature file's route, preconditions and gotchas instead of discovering them. The drive skill already reads matching feature files before driving; this spec makes the defect path hand it the resolved feature rather than leaving drive to rediscover which feature the report is about. [inferred]
- The resolution result (the chosen `Surface` and sub-feature ID, or `unmapped`) travels with the reproduction evidence as a resolved-feature record, so the fix, the review and the PR reuse it. This is the shared carrier the "feature map across live-app routes" spec extends to its routes. [inferred]
- The map stays owned by `/flow-next:features`, the only seeder and maintainer. Bug intake reads it and never writes it; a route that no longer matches the live app files the existing `feature-map-drift` memory note that QA already uses. The one other writer, work's update of entries its own change altered, is defined by the "feature map stays current" spec. [inferred]
- Discovery is by existence check only, the same as QA and drive: no config key, no registration. [paraphrase]

## Edge Cases & Constraints
<!-- scope: technical -->

- No feature map in the repo: behaviour is exactly today's, at the cost of one existence check.
- The report matches no mapped feature: fall back to today's live discovery and record `unmapped`. A missing feature is information for the next `/flow-next:features` maintain pass, not an error.
- The report plausibly matches more than one feature: name the candidates and try them in order of specificity; record the one that reproduced.
- The mapped route is stale (the live app no longer matches the file): continue with live discovery for this run and file the drift entry; never edit the map from flow.
- A screenshot with no readable page title or route: match on visible content (headings, table columns, controls) against feature descriptions; if nothing matches, treat it as unmapped.
- The map says how to reach a feature, never what the bug is: the report and the reproduction remain the evidence for the defect.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** When flow routes a reported defect that still needs a reproduction and the repo has a feature map, the reproduction first resolves the report to a mapped feature (by `Surface` plus sub-feature ID) and drives the reproduction along that feature file's route, preconditions and gotchas. Errors: no plausible match → live discovery as today, recorded as `unmapped`; several plausible matches → candidates named and tried in order of specificity, the one that reproduced recorded; a stale route → live discovery for this run plus a `feature-map-drift` memory entry, with the map left unedited. [paraphrase]
- **R2:** A report that arrives with a screenshot is matched on the screenshot's visible content as well as its text, so a screenshot with no page title or URL can still resolve to a mapped feature. Errors: an unreadable or unmatched image falls back to text-only matching, then to `unmapped`. [paraphrase]
- **R3:** In a repo with no feature map, the defect route behaves exactly as it does today, with no added reads beyond one existence check. No error surface beyond that check. [paraphrase]
- **R4:** The resolved feature (or `unmapped`) is recorded with the reproduction evidence and is visible to the later stages of the same run (fix, review, PR), so none of them re-derives navigation to the defect. No error surface beyond R1's `unmapped` value. [inferred]
- **R5:** The change is measured as a speed improvement: on a fixture app with a feature map, a pre-registered comparison of flow's defect intake with and without the map shows fewer turns (or less wall time) to a reproduced defect, with the reproduction success rate no lower. The measurement and its result are published with the change, whichever way it falls. [paraphrase]

## Boundaries
<!-- scope: business -->

- Only flow's bug intake. Other conductor routes that could read the map (performance baselines, where-is-this questions, work's own verification, PR evidence) are not in this spec; they may be added later as further flow improvements. [paraphrase]
- Framed and claimed as a speed and efficiency gain, not as a higher success rate. [paraphrase]
- No richer feature-entry contract and no app-specific drive helper: both were tested in the same study and showed no gain. [paraphrase]
- Bug intake never seeds, maintains or edits the feature map; `/flow-next:features` stays the only seeder and maintainer and stays user-invoked. [inferred]
- The map is never the source of what to prove: the report and the reproduction stay the defect's evidence. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer sees `/flow-next:flow` as the product's strongest surface and wants to invest in it ("the flow-next:flow thing is really good and we need to lean into it"). [user] This spec is deliberately the first, narrow piece of that: the map-backed bug intake only, framed as a speed improvement, with room to add further flow improvements later if they are pursued. [paraphrase] Feature maps are expected to pay off most in large repos, where finding the broken place is the expensive part of a bug report. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: the feature map stays current, the feature map across live-app routes, a hardened defect route, the hill-climb loop, answering questions by experiment, sharper handovers, a read-only PR status answer, diagnosing a captured profile, and resume and review hygiene. It depends on "the feature map stays current", which must land first so intake reads a map that is kept true; the live-app-routes spec and the defect route spec depend on this one.

## Strategy Alignment

Serves the approach line that `/flow-next:flow` is the one dial on the default path: it reads whatever the user has and routes it, and this makes the defect route cheaper when a map exists. Serves the **Self-improving through normal work** track: the feature map is a compounding surface, and this gives it a second everyday reader beside QA, so the navigation knowledge pays off on every bug report rather than only on QA runs.

## Strategy Conflicts

None found.
