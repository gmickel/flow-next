# Diagnose a captured profile, trace or dump

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 40% [paraphrase], 50% [inferred] -->

People often arrive with evidence already captured: a CPU profile, a browser performance trace, a heap snapshot, a crash dump, a flame graph. `/flow-next:flow` has no route for that. The nearest row, measured slowness, assumes the agent will capture a baseline itself and then fix; it does not describe what to do with an artifact someone else recorded, and it pushes toward a fix when the honest deliverable may only be a diagnosis.

This spec adds that route. The deliverable is a diagnosis: what the artifact shows, where the time or memory goes, which source lines are responsible, and how confident the conclusion is. A conclusion stays a hypothesis unless a before-and-after pair confirms it. A fix is a separate, explicit next step, not an assumption. The maintainer asked for this set of flow improvements to be captured and done properly.

Target user: an engineer who hands flow a captured artifact and a question ("why is this slow?", "what is holding this memory?", "what crashed?").

## Architecture & Data Models
<!-- scope: technical -->

- **A new routing row** for "a captured profile, trace, heap snapshot or crash dump handed over for diagnosis". Its route is diagnose-only: load the artifact, answer the question, label confidence, and stop with a recommended next step. It sits beside the measured-slowness row and the read-only question row, and it shares the judge's verbatim-cell contract like every other row. [paraphrase]
- **Load into a queryable form.** The agent converts the artifact into something it can query rather than skim (for example tabular rows of frames, samples, allocations or spans that can be sorted, grouped and filtered), using tools the repository or the host already has. When no suitable tool exists, the agent says so and works from what it can read. flowctl adds no parser and no dependency. [inferred]
- **Trace to source.** Hot frames, dominant allocation sites or the crashing frame are mapped to source files and lines in the current checkout, noting when the artifact was captured on a different revision. [paraphrase]
- **Confidence labels.** Every conclusion carries one of: *observed* (the artifact directly shows it), *inferred* (a likely cause the artifact supports but does not prove), or *confirmed* (a before-and-after pair of artifacts or measurements shows the effect). Nothing is labelled confirmed from a single artifact. [paraphrase]
- **Deliverable.** A diagnosis report in the conversation (and, when a spec is created from it, in the spec): the question, the artifact's provenance (what, when, which revision, how captured if known), the top findings with their labels and source locations, what the artifact cannot show, and the recommended next route (for example the measured-slowness route to fix, the hill-climb route to drive a number down, or a defect route when a crash has a clear cause). [inferred]

### Worked example

A user drops `boot.cpuprofile` and asks why the desktop app takes 6 seconds to show its first window.

The agent loads the profile into sortable rows of self time and total time per function. Total time under the startup entry point is 5.8 seconds. The top self-time frames are a synchronous directory walk (2.1 s) and JSON parsing of a large settings cache (1.4 s). Mapping frames to source: the walk is the plugin loader scanning the whole user data folder; the parse is the settings cache read on the main thread. The profile was captured on a revision two weeks old; the loader code is unchanged since, the cache code has changed, and the report says so.

Findings: *observed*, 36% of startup is the plugin directory walk; *observed*, 24% is parsing the settings cache; *inferred*, the walk scans far more files than it loads plugins from, because the profile shows per-file stat calls but only a handful of plugin loads. Nothing is *confirmed*. Recommended next: the hill-climb route with first-window time as the metric, starting from the plugin-scan hypothesis, or the measured-slowness route for a single targeted fix.

## Edge Cases & Constraints
<!-- scope: technical -->

- An artifact format the agent cannot read with available tools: report the format, what would be needed, and anything that could still be read (for example symbol names in a text export).
- Symbols missing (minified or stripped builds): report that attribution is limited and to what; do not guess source lines.
- The artifact comes from a different revision or environment than the checkout: every source attribution states the difference.
- Sensitive content in a heap snapshot or crash dump (tokens, personal data): the report quotes only what the diagnosis needs and never pastes raw memory contents into specs, PRs or trackers.
- `flow --auto` never takes raw intent; this route is reached attended, or through a spec that already names an artifact and a question.
- No fix is written on this route. A request to fix routes onward explicitly.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Flow recognises a handed-over profile, trace, heap snapshot or crash dump with a question as its own starting state and routes it to diagnosis, not to a fix. Errors: an artifact with no question → one attended question asking what to find out; an ambiguous input → the existing routing fallback. [paraphrase]
- **R2:** The diagnosis loads the artifact into a queryable form using tools the repository or host already provides, and states which tool or method it used. Errors: no usable tool → the report says which format and what would be needed, and diagnoses from whatever can be read. [inferred]
- **R3:** Findings are mapped to source locations in the current checkout, and any revision or environment difference between the artifact and the checkout is stated on each affected finding. Errors: missing symbols → attribution limited and stated, never guessed. [paraphrase]
- **R4:** Every finding carries exactly one label (observed, inferred, confirmed), and confirmed is used only with a before-and-after pair. No error surface beyond an unlabelled finding failing the check. [paraphrase]
- **R5:** The report includes the question, the artifact's provenance, the labelled findings, what the artifact cannot show, and one recommended next route; no code change is made on this route. No error surface beyond R1-R4. [inferred]
- **R6:** Raw sensitive content from heap snapshots or crash dumps is never copied into specs, PRs or tracker comments; only the minimum needed to explain a finding is quoted. No error surface beyond that rule. [inferred]
- **R7:** The routing table gains the row with the judge's matching criteria and presentation, and the routing pin tests pass; the pipeline-variations guide and the flow-next.dev route pages describe the route with a worked example. No error surface beyond the pin tests. [inferred]

## Boundaries
<!-- scope: business -->

- Diagnosis only; fixing routes onward to measured slowness, hill climb or the defect route. [paraphrase]
- No profiler, parser or format library is added to flowctl; tools come from the repository or host. [inferred]
- Capturing new profiles is the measured-slowness and hill-climb routes' job, not this one's. [inferred]
- No new routing reference file; the route is a row in the routing table. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer asked for all of the flow improvements from this review to be captured and done properly ("so all of the above i want captured and the make sure everything is excellent"). [user] Captured artifacts are common evidence and flow currently has no honest way to handle them: it either ignores them or jumps to a fix. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: keeping the feature map current, feature-map-aware bug intake (fn-261), the feature map across live-app routes, a hardened defect route, the hill-climb loop, answering questions by experiment, sharper handovers, a read-only PR status answer, and resume and review hygiene. It stands alone; its recommended next routes may point at the hill-climb and defect specs once they ship.

## Strategy Alignment

Serves the approach line that flow reads whatever the user has, including artifacts, and routes it through one shared routing reference; evidence over narration is kept by the confidence labels.

## Strategy Conflicts

None found.
