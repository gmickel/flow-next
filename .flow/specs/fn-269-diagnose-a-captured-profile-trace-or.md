# Diagnose a captured profile, trace or dump

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 60% [paraphrase], 30% [inferred] -->

People often arrive with evidence already captured: a CPU profile, a browser performance trace, a heap snapshot, a crash dump. Flow should answer the question from the artifact and stop at a diagnosis with a recommended next route, rather than jump to a fix. [paraphrase]

A capable agent already knows how to read these. What it needs is the route's stance in one sentence: answer from the artifact, map findings to source, call a cause confirmed only when a before-and-after pair shows it, quote no sensitive memory, and hand fixing to the route that owns it. pstack covers the same job in a 14-line playbook (`trace-forensics.md`). [paraphrase]

Target user: an engineer who hands flow a captured artifact and a question ("why is this slow?", "what is holding this memory?", "what crashed?"). [inferred]

## Architecture & Data Models
<!-- scope: technical -->

- **One sentence in the existing read-only question row.** The route matrix's read-only question row's Route cell gains a sentence for a handed-over profile, trace, heap snapshot or crash dump: load it into a queryable form with tools the repo or host already has, map findings to source (stating any revision difference), treat a cause as confirmed only with a before-and-after pair and as the strongest supported hypothesis otherwise, quote only what the diagnosis needs from sensitive dumps, write no fix, and recommend the next route (measured slowness, hill climb, or the defect route). [paraphrase]
- **Nothing else changes in routing.** The starting-state and signal cells the judge embeds stay as they are, so the judge, its pin tests and the routing-accuracy study are untouched. [paraphrase]

### Worked example

A user drops `boot.cpuprofile` and asks why the desktop app takes 6 seconds to show its first window. The agent loads the profile into sortable per-function rows: a synchronous directory walk takes 2.1 s and parsing a settings cache 1.4 s. The walk maps to the plugin loader scanning the whole user data folder; the profile shows per-file stat calls but only a handful of plugin loads, so the likely cause is an over-broad scan. The profile is two weeks old; the loader is unchanged since, the cache code is not, and the answer says so. Nothing is confirmed without a before-and-after pair. Recommended next: the hill-climb route on first-window time.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The read-only question row's Route cell carries the captured-artifact sentence; its starting-state and signal cells are unchanged, and the routing pin tests pass. [paraphrase]
- **R2:** No new routing row, judge kind, reference file, confidence-label scheme or check is added. [paraphrase]
- **R3:** The pipeline-variations guide and the flow-next.dev route page mention the captured-artifact case with a short example like the one above. [inferred]

## Boundaries
<!-- scope: business -->

- Diagnosis only; fixing routes onward. [paraphrase]
- No parser, profiler or format library in flowctl. [inferred]
- No required structure on the diagnosis, per STRATEGY.md "Agent first". [paraphrase]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

Trimmed on 2026-09-28 before build. The first version added a new routing row and judge kind (forcing a routing-accuracy study rerun) and required exactly one of three confidence labels on every finding, with an unlabelled finding failing a check. The maintainer's direction is agent first, without machinery ("agentic first, don't overengineer machinery"). [user] The route's stance fits in one sentence in the row that already covers questions. [paraphrase]

Delivery order: 9 of the fn-261..fn-270 set; independent; route direct, `/flow-next:work fn-269-diagnose-a-captured-profile-trace-or --no-plan`.

## Strategy Alignment

Serves "Agent first" and the approach line that flow reads whatever the user has, including artifacts.

## Strategy Conflicts

None found.
