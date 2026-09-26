# Answer questions by experiment in refine and prototypes

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 50% [paraphrase], 40% [inferred] -->

Many questions a spec raises are not the user's to answer: they are facts the agent could observe by running something. How long does this take? Does this layout fit at 320 pixels? Does this parser accept that input? Does this eval separate the two variants? Flow's conductor already settles an observable design fork with a prototype before asking, and refine already carries an empirically-answerable rule. But refine's shared question taxonomy does not list that category, the rule does not name layout, performance or eval separation, and its results are filed under the codebase audit section as if they had been read from source. Flow's prototype step compares one idea at a time and does not gather prior art when the design space is open.

This spec makes "answer it by running something" a first-class, auditable way to resolve a question in refine, and strengthens flow's prototype step so competing ideas are compared side by side. The result is fewer questions to the user, answered by evidence instead of opinion.

Target user: anyone refining a spec or settling a design fork through flow.

## Architecture & Data Models
<!-- scope: technical -->

- **Refine taxonomy.** The shared question taxonomy gains a fourth category, experiment-answerable: behaviour, timing, layout, output, performance, and whether an evaluation separates two options. Before asking the user, refine classifies the question; an experiment-answerable question runs a throwaway experiment and records the outcome instead of asking. Genuine product and preference calls still go to the user. [paraphrase]
- **Safety.** The existing rule stays: an experiment runs only when it is read-only or fully disposable. Anything stateful, destructive or external becomes a user question. Experiments run in a gitignored scratch location under the flow directory and are discarded or folded into the spec as evidence, never shipped. [paraphrase]
- **Audit trail.** A new auxiliary section, `## Resolved via Experiment`, records each resolution: the question, what was run, what was observed, and the decision it settled. It joins the other refine-written auxiliary sections in the template's list, the repository's own spec template override, and refine's preserve-byte-for-byte rule, so later passes keep it. [inferred]
- **Flow's prototype step.** When a fork is observable, the prototype builds the competing variants behind one switcher (a toggle, flag or keypress that swaps between them, each labelled) so they are compared in one place; when the design space is open, it first gathers references and prior art and lets the user pick a direction before building. A prototype stays evidence, never a deliverable. Chart's single-artefact rule still holds: variants behind one switcher are one artefact. [paraphrase]
- **Autonomy.** Unattended runs do not dispatch refine; under `flow --auto` a preference fork still stops with `NEEDS_HUMAN`, and a cheap reversible prototype may still run as today. [inferred]

### Worked example

Refining a spec for a new search box, three questions come up. "Should results update on every keystroke or after a pause?" The agent classifies it as experiment-answerable: it builds a throwaway page with both behaviours behind a toggle, types a 12-character query against the local index, and measures that per-keystroke search takes 180 ms per update and visibly stutters, while a 150 ms pause feels immediate. It records the question, the experiment and the numbers under Resolved via Experiment, and writes "update after a 150 ms pause" into the spec. "Does the existing tokenizer handle accented names?" It runs the tokenizer on five sample names, observes two are split wrongly, and records that as a constraint. "Should search include archived projects?" That is a product call, so it asks the user.

## Edge Cases & Constraints
<!-- scope: technical -->

- An experiment that needs network access, credentials or a shared service: not disposable, so it becomes a user question.
- An experiment whose result is inconclusive (noise larger than the difference): recorded as inconclusive and the question goes to the user with the data.
- The routing references folder is a fixed set; the prototype changes edit the existing prototype reference rather than adding a file.
- The template auxiliary list, the repository's template override and the tests that pin both change together.
- The generated agent mirrors are regenerated, not hand-edited.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Refine's shared question taxonomy includes the experiment-answerable category covering behaviour, timing, layout, output, performance and evaluation separation, and refine runs a disposable experiment instead of asking when a question falls in it. Errors: a stateful, destructive or external experiment → asked as a user question; an inconclusive result → asked with the data attached. [paraphrase]
- **R2:** Each experiment resolution is recorded under `## Resolved via Experiment` with the question, what was run, what was observed, and the decision; the section is in the template's auxiliary list and the repository override and is preserved by later passes. No error surface beyond the pinned template tests passing. [inferred]
- **R3:** Experiment artefacts live in a gitignored scratch location and are discarded or folded into the spec as evidence; none ships as product code. No error surface beyond that rule. [paraphrase]
- **R4:** Flow's prototype step builds competing variants behind one labelled switcher and, when the design space is open, gathers references and prior art for the user to pick a direction before building. Errors: a fork with only one viable variant → a single prototype as today. [paraphrase]
- **R5:** Product and preference calls still reach the user, and `flow --auto` still stops with `NEEDS_HUMAN` on a preference fork. No error surface. [inferred]
- **R6:** The refine and flow skill pages and the explore-first and prototype guides on flow-next.dev describe experiment-answerable questions and the switcher, with an example like the one in this spec. No error surface. [inferred]

## Boundaries
<!-- scope: business -->

- No experiment touches shared state, credentials or external services. [paraphrase]
- No new routing reference file. [inferred]
- A prototype is never promoted to implementation; the real build goes through work. [paraphrase]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The maintainer asked for this set of flow improvements to be captured and made excellent ("definitely do all of this", "make sure everything is excellent"). [user] Every question the agent can answer by observation is one less interruption for the user and one more decision grounded in evidence. [paraphrase]

This spec is one of a set captured together to strengthen `/flow-next:flow`: the feature map stays current, feature-map-aware bug intake (fn-261), the feature map across live-app routes, a hardened defect route, the hill-climb loop, sharper handovers, a read-only PR status answer, diagnosing a captured profile, and resume and review hygiene. It stands alone.

## Strategy Alignment

Serves the approach line that material product or authority choices need refinement while everything else stays with the owner: experiments move factual questions off the user.

## Strategy Conflicts

None found.
