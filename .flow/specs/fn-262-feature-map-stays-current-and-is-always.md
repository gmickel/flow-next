# Feature map stays current and is always recommended

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 25% [user], 45% [paraphrase], 30% [inferred] -->

The feature map (`.flow/features/`, written by `/flow-next:features`) records how a user reaches each feature of the app and how an agent drives it. More and more of `/flow-next:flow` will read it: bug intake first (fn-261), then the other routes that touch a running app. A map that goes stale costs turns in every one of those routes instead of saving them.

Today nothing keeps it current. The maintain pass is user-invoked only, which is right for a pass that live-drives every feature, but nothing tells anyone when to run it. Only QA reports drift. Flow's routing row recommends a maintain pass when a map is "due", and nothing defines "due". Feature files carry no record of when they were last proven, and drift notes are never retired, so any count of them only grows. Setup recommends seeding a map only when live QA is on, and prime never mentions it.

The project's own strategy says improvement that depends on remembering an extra command does not happen. This spec makes the map stay true as a side effect of normal work, gives "due" a real trigger, makes setup and prime always recommend seeding, and documents how the map is kept current. It lands before the specs that spread map use across flow, because spreading a map that goes stale would cost more than it saves.

Target user: every repository with a user-facing surface that runs Flow-Next, and the maintainers who keep its map.

## Architecture & Data Models
<!-- scope: technical -->

- **Last-proven provenance.** Each feature file gains one optional line directly under its `**Surface:**` line: `**Last proven:** <date> at <short commit>`, written whenever a live drive proves the file's route (seed, maintain, or the work step below). Files without it are treated as never proven. The line names no source paths, so the entry contract's no-implementation rule holds. [inferred]
- **Work updates the map with the code.** When a spec's change alters how a user reaches a mapped feature (a renamed control, a moved page, a new entry point, a removed sub-feature), work updates that feature file in the same change and proves the new route with one live drive through the drive skill, then refreshes the file's last-proven line. The step runs at the conductor's quality phase after all tasks complete, so no task has to declare the map directory and no parallelism is lost. Only entries the change altered are touched; nothing undriven enters the map. When the app cannot be started, the file is left unchanged and a drift note records the expected change for the next maintain pass. [paraphrase]
- **Every map reader reports drift.** Any stage that drives from the map (QA today; bug intake, the defect route's live proof, and the other live-app routes as they land; the drive skill itself) files the existing drift note when a mapped route no longer matches the live app. The note keeps its existing title identity and tag unchanged, so deduplication and the maintain pass keep working. Readers still never edit the map mid-run. [paraphrase]
- **Drift notes are retired.** When the maintain pass (or the work step above) proves a corrected route, it marks the matching drift note stale through the existing memory command, so an open count means open drift. [inferred]
- **"Due a maintain pass" gets a trigger.** Flow's what-next reading recommends `/flow-next:features` (maintain) when either holds: at least one open drift note exists, or a mapped feature's last-proven commit is older than a threshold of commits that touched the app's user-facing surface. The threshold is a setting with a sensible default. Flow recommends; it never dispatches the skill, because the skill stays user-invoked under every autonomy marker. [paraphrase]
- **Always recommend seeding.** Setup always prints the `/flow-next:features` line at the end of setup, no longer only when live QA is on: it recommends seeding when no map exists, and a maintain pass when a map exists and is due. Prime's report always carries the same one-line recommendation beside its QA-readiness line. [paraphrase]
- **Documentation.** The install and quickstart pages mention the recommended seed step and what it buys. A "keep the map current" guide explains the three mechanisms (work updates, drift reports, the due trigger), when to run maintain, and how to run it on a schedule from a host loop the human starts. The feature-map skill page, the "how it compounds" page, the live-QA guide and the in-repo architecture doc are updated to match. [paraphrase]

### Worked example

A spec renames the "Settings" sidebar button to "Preferences" and moves notification settings to their own page. Work finishes the tasks. At the quality phase it sees the change altered two mapped routes: the settings shell entry point and the notification controls. It opens the running app, reaches Preferences by the new name, reaches the new notifications page, confirms the controls, rewrites both feature files' "How to get to it" and "Driving it" sections, refreshes their last-proven lines to today at the new commit, and marks the one drift note QA filed last week about the old button name as stale. The PR shows the map diff beside the code diff.

A month later a teammate asks flow what to do next. Three drift notes are open (bug intake found two stale routes, QA found one) and the checkout page's file was last proven 120 commits ago while the checkout code changed 14 times. Flow recommends `/flow-next:features`; the teammate runs it, and the maintain pass proves the fixes and retires the notes.

## Edge Cases & Constraints
<!-- scope: technical -->

- No map in the repository: the work step, the drift reporting and the due trigger do nothing beyond one existence check; setup and prime recommend seeding.
- A repository with no drivable surface (a library): the setup and prime line still prints; the seed pass itself refuses with its existing reason, so nothing is written.
- The app cannot be started during work's update step: the map is left unchanged, a drift note records the expected change, and the work run is not blocked by it.
- The change alters a mapped route but work cannot tell which file maps it: the step records a drift note naming the changed surface rather than guessing an edit.
- Unattended runs (`flow --auto`, land, Ralph) never dispatch `/flow-next:features`; the work update step runs inside work and follows work's own autonomy rules.
- Memory disabled: drift notes cannot be filed or retired; the due trigger falls back to the last-proven age alone, and stages record drift in their run notes as today.
- Existing maps without last-proven lines stay valid; they read as never proven until a drive proves them.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Feature files accept an optional `**Last proven:** <date> at <short commit>` line under the surface line; seed, maintain and work's update step write it whenever a live drive proves the file's route, and files without it read as never proven. Errors: a malformed line is treated as absent and reported by the maintain pass. [inferred]
- **R2:** When a spec's change alters how a user reaches a mapped feature, work updates only the affected feature files in the same change, proves each new route with one live drive, and refreshes their last-proven lines. Errors: app not startable → map unchanged plus a drift note describing the expected change; affected file unclear → a drift note naming the changed surface, no guessed edit. [paraphrase]
- **R3:** Every stage that drives from the map files the existing drift note (same title identity and tag) when a mapped route does not match the live app, and none of them edits the map mid-run. Errors: memory disabled → drift recorded in the stage's run notes. [paraphrase]
- **R4:** A maintain pass or work update that proves a corrected route marks the matching drift note stale. No error surface beyond memory being disabled, in which case nothing is marked. [inferred]
- **R5:** Flow's what-next recommendation names `/flow-next:features` when a map exists and at least one drift note is open, or when any feature's last-proven commit is older than the configured threshold of surface-touching commits; the recommendation never dispatches the skill. Errors: memory disabled → the age condition alone applies. [paraphrase]
- **R6:** Setup always prints the `/flow-next:features` recommendation (seed when no map exists, maintain when one exists and is due), regardless of the live-QA setting, and prime's report always carries the same recommendation. No error surface beyond a repository with no drivable surface, where seed's own refusal applies. [paraphrase]
- **R7:** The install and quickstart pages mention the always-recommended seed step, and a guide explains how the map is kept current (work updates, drift reports, the due trigger, when and how to run maintain, running it on a host loop); the feature-map, compounding, live-QA and architecture docs agree with it. No error surface. [paraphrase]
- **R8:** fn-261's boundary is amended so that `/flow-next:features` stays the only seeder and maintainer while work may update entries its own change altered under R2; no other map writer is introduced. No error surface. [inferred]

## Boundaries
<!-- scope: business -->

- The full maintain pass stays user-invoked; no pipeline stage, post-merge hook or autonomous driver runs it. [paraphrase]
- No new map writer besides work's scoped update of entries its own change altered. [inferred]
- The map stays navigation only; specs remain the intent and live evidence remains the proof. [inferred]
- Seeding is recommended, never run automatically at setup: it launches and drives the live app. [paraphrase]
- No source paths enter feature files; provenance is a date and a commit. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer wants feature maps across most of flow's routes to cut wall-clock time ("we would add the features thing into most routes going forward in hope of more efficient token usage and wall-clock"), asked whether the map is kept up to date automatically ("is features kept up to date automatically?"), wants seeding always recommended ("new would be to always recommend it"), and ruled that keeping it current must come first ("it should be done first or within another spec that does stuff with feature"), with downstream documentation ("if we are always recommending it, we should mention that in the install/quickstart places", "how to keep it up to date etc"). [user] The study in this conversation found the map roughly halves turns on locate-heavy reports while token cost per run stayed flat, so the benefit is wall-clock and turns; a stale map would erase it. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: feature-map-aware bug intake (fn-261), the feature map across live-app routes, a hardened defect route, the hill-climb loop, answering questions by experiment, sharper handovers, a read-only PR status answer, diagnosing a captured profile, and resume and review hygiene. fn-261 and the live-app-routes spec depend on this one.

## Strategy Alignment

Serves **Self-improving through normal work** directly: the map stays true as a side effect of work, drift reports and a due trigger replace remembering an extra command, and the maintain pass becomes an occasional clean-up rather than the only upkeep.

## Strategy Conflicts

None found. The strategy's "never a manual compound/refresh ceremony" is the reason for this spec.
