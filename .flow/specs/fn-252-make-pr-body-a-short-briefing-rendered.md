# make-pr body: a short briefing rendered from the aid artifact

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 40% [paraphrase], 60% [inferred] -->

make-pr exists to make reviewing a pull request easier for a person. Today its body tries to be the full record. On a 14-file mechanical pull request the first six rows of the proof table were machine identity (an artifact id, two 40-character SHAs, "deterministic file stats", "deterministic membership", a file total). The file table had seven columns, its Evidence column repeated the same five references on every row, and its diff links pointed at blobs. Because the pull request was under the size threshold, the compact form dropped the four groups the agent had authored and kept the machine data. The thesis rendered an HTML entity where an apostrophe belonged. That body should have been about 15 lines: the thesis, one file tree with a purpose per file, and the verification line. An open report in this repository measures bodies at 2,700 to 3,700 words.

The rule this spec sets: a line stays in the rendered markdown only if a reviewer, technical or not, would act differently after reading it. What only a machine needs stays in the stored artifact. Empty sections never render, placeholders included. A small pull request gets a small body.

There are two layers and one authored object. The markdown body is a briefing of about 40 lines for any reviewer, on any forge, in a terminal. The stored aid artifact is the full walkthrough (every file, attention classes, provenance) for the HTML lens, the validator and any downstream projector. flowctl renders the briefing from the artifact, so the body and any other view of the same artifact cannot drift. The briefing uses the shapes the visual skill already settled on: one screen, fewer and more honest nodes, diff-fenced trees that render natively on every forge and in a terminal.

The make-pr skill loads about 2,800 lines of instructions on a run, the largest cost of every run. With a short rendered briefing most of that text has nothing left to govern.

## Architecture & Data Models
<!-- scope: technical -->

- flowctl renders one briefing form for every pull-request size. The compact and full forms and the size threshold that chose between them are retired. There is still exactly one rendering of a given artifact and no discretionary choice of form. [paraphrase]
- The artifact gains four optional authored fields (what changes for a user or operator, the blast radius, tradeoffs, open items) and an optional outcome on each proof cell with three values: pass, fail, unverified. A verification step that nobody ran is a proof cell with outcome unverified, so Verification has one list. All of it is additive; the stored schema version stays 1 and the artifact path is unchanged. [user]
- Attention classes carry the review plan: canonical means must read, mechanical and generated mean safe to skim. There is no separate review-plan section. [inferred]
- Identity data that a tool needs (artifact id, base and head) rides in one HTML comment, invisible in the rendered body. [inferred]
- The HTML lens and other readers of the stored artifact are unaffected; only the markdown rendering changes. Nothing is known to parse the body text, so the markdown can change freely. [inferred]

## API Contracts
<!-- scope: technical -->

Briefing sections, in this order, each omitted when it has no content:

1. Why: the thesis, intent and approach, one or two short paragraphs.
2. What changes for a user or operator: the section for a non-technical reviewer.
3. Scope: one diff-fenced file tree per group, with a one-line purpose and requirement id on each described file; the remaining files of a group collapse to one line that counts them and says whether they are mechanical or not described. One coverage line maps each requirement to the groups that evidence it and marks an uncovered one. The per-criterion table renders only when a requirement is unevidenced or undeclared.
4. Blast radius: one to three sentences on who or what the change touches and why it is safe or risky.
5. Verification: a checklist of the proof cells. A cell with outcome pass is ticked; fail and unverified render unticked with their note; a cell with no outcome renders as a plain line with no tick.
6. Tradeoffs: only rejected alternatives a reviewer would otherwise ask about.
7. Open items: only when something is unfinished.

## Edge Cases & Constraints
<!-- scope: technical -->

- An artifact stored before this change has none of the new fields. It renders in the new form with those sections omitted. [inferred]
- A pull request with many groups and many described files can exceed the line budget. The renderer decides what collapses, deterministically, lowest attention first; the agent does not. [inferred]
- Prose is rendered so that apostrophes and quotation marks appear literally. Characters that could inject markup stay neutralized. [inferred]
- A structural diagram appears only when structure actually changed, and the diff-fenced structural sketch is preferred over Mermaid because it renders everywhere. [paraphrase]
- The land redesign has make-pr commit the spec close on the branch. The artifact is bound to the head, so that commit must exist before the artifact is composed, or every artifact is stale at birth. [paraphrase]
- Tests in this repository pin skill and documentation wording, and generated mirrors follow the skill text. Both change with this spec. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** flowctl renders one briefing form from an aid artifact regardless of pull-request size; the compact and full forms and their threshold are removed, and no flag or config key selects a form. The same artifact always renders the same bytes. Errors: an artifact that fails validation renders nothing and make-pr falls back as it does today. [paraphrase]
- **R2:** The briefing contains the seven sections named in API Contracts, in that order, and a section with no content is omitted entirely, with no heading and no placeholder sentence. Errors: an artifact with only a thesis renders only the Why section; an artifact stored before this change renders without the new sections. [paraphrase]
- **R3:** Scope renders each group as a diff-fenced file tree with a one-line purpose and requirement id on each described file, collapses the group's remaining files to one counted line that distinguishes mechanical files from files not described, and renders one coverage line. The per-criterion coverage table renders only when a requirement is unevidenced or undeclared. Errors: a group with no described files renders as its title and one counted line; an uncovered requirement is named on the coverage line. Superseded in part 2026-09-21 by the maintainer: described files render as a linked list that wraps, every group renders, and coverage names groups. [paraphrase]
- **R4:** Verification renders the proof cells as a checklist. The renderer ticks only a cell whose outcome is pass, renders fail and unverified unticked with their note, and treats a cell with no outcome as untickable, so a failed or inconclusive gate is never rendered as ticked by construction and not by an authoring convention. The author draws the cells from task evidence and review receipts. Errors: with no proof cells the section is omitted; an artifact stored before this change has no outcomes, still validates, and renders its proof as plain lines with no ticks; an outcome outside the three values is rejected naming the cell. [user]
- **R5:** The rendered body no longer contains the artifact id, base and head SHAs, membership and file-stat rows, the per-row Evidence column, the branch line and task count, the high-churn critical-changes list, the review-plan section, memory, glossary and strategy notes, or the visible generated-by footer line. Identity data sits in one HTML comment. An invisible marker comment stays only if a reader of it remains after the land redesign. Errors: no error surface beyond R1. [paraphrase]
- **R6:** The briefing flowctl renders is at most 40 lines for any artifact. When the content exceeds the budget the renderer collapses entries deterministically, lowest attention first, and the counted lines reflect what was collapsed. Errors: the Why section and the coverage line are never collapsed; an artifact whose thesis alone exceeds the budget renders the thesis in full and collapses everything else to counted lines. [inferred] Superseded 2026-09-21 by the maintainer: the body renders all authored content; only described rows are capped, at ten per group (#458).
- **R7:** The artifact accepts four optional authored fields (what changes for a user or operator, blast radius, tradeoffs, open items) and an optional outcome (pass, fail, unverified) on each proof cell. There is no separate field for steps not verified. Artifacts with and without any of them validate, the stored schema version stays 1, and the artifact path is unchanged. The consumer documentation lists the additions as additive. Errors: a new field of the wrong type is rejected naming the field; an unknown field is handled as the validator handles unknown fields today. [user]
- **R8:** Rendered prose shows apostrophes and quotation marks literally, and characters that could inject markup into the pull-request body remain neutralized. Errors: no error surface beyond that stated. [inferred]
- **R9:** The make-pr instruction text loaded on an ordinary run, references included and the opt-in HTML lens reference excluded, is under 600 lines. The instructions for the removed body sections are deleted, not moved. Errors: no error surface beyond R1. [inferred]
- **R10:** make-pr composes the aid artifact after the spec-close commit from the land redesign exists on the branch, so the artifact's head equals the pull request's head when it opens. The land redesign spec states the same ordering. Errors: a failed close stops make-pr before the artifact is composed; a spec with incomplete tasks has no close commit and composes as today. [paraphrase]
- **R11:** The PR for this spec reports make-pr measured after this spec's changes on the same fixed pull request, with the same model and method as the sibling input spec's measurement record (output tokens, tool calls, wall-clock time, at least three runs, medians), and compares three points: make-pr before either spec, after the input spec, and after this spec. Negative results are kept. The changelog credits the reporter of the open body-length report, which this change resolves. Errors: no error surface. [paraphrase]

## Boundaries
<!-- scope: business -->

- The input side of the artifact (filled fields, sparse rows, inherited references, validation errors, ignore rules, reuse at an unchanged head) belongs to the sibling input spec. [inferred]
- No split of make-pr into a markdown path and a JSON path. [paraphrase]
- No flag, config key, or instruction-file switch that selects a body form or a length. [paraphrase]
- No change to the HTML lens. [inferred]
- No schema version bump. [paraphrase]
- No fix for the per-clone limit of ignored artifacts. [paraphrase]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
<!-- scope: business -->

- Everything that lands in the markdown has to be of direct use to the reviewer, technical or not. What is not does not belong there. [paraphrase]
- make-pr should build on what the visual skill learned and produce something right for a forge's markdown and for downstream views of the same artifact. [paraphrase]
- The size threshold between compact and full bodies was declared closed two days before this spec. It is retired here because one briefing form keeps the reason for that ruling (one artifact renders one way, with no discretionary form) while removing the case where a small pull request lost its authored groups. [paraphrase]
- This spec is worked after the land redesign and after the sibling input spec. [paraphrase]

### Implementation Tradeoffs
<!-- scope: technical -->

- Rejected: keeping the threshold and using the briefing only for large pull requests. Compact is the form that throws the judgment away. [inferred]
- Rejected: letting the agent write the body as free markdown. flowctl rendering from the artifact is the one piece of machinery worth keeping, because it is what stops the body and other views of the artifact from drifting. [paraphrase]
- Decided 2026-09-21: Tradeoffs and Open items had no source in the artifact, and proof cells carried no pass or fail, so the first draft of R7 (three fields) could not satisfy R1, R2 and R4 together. The artifact gains tradeoffs and open items as authored fields and an outcome on proof cells, and the separate steps-not-verified field is dropped. Rejected: rendering those sections from live flow state, which would make identical bytes depend on flow state and drop the sections for every other reader of the artifact; and ticking from a prose convention, which leaves R4 to the author's memory. [user]
- Rejected: a schema version bump for the new fields. A reader that does not know a version falls back to a degraded view, and additive optional fields reach the same end without that cost. [paraphrase]
- The 600-line bound follows the land redesign, which bounds its own skill text the same way. make-pr does more than land (pull-request creation seams, chain and stack linking, the tracker touchpoint), so its bound is higher. An ordinary run loads about 2,345 lines today, so 600 is already a fourfold cut; it is a ceiling and the plan may tighten it. [paraphrase]

## Strategy Alignment

- Design principle "The artifact is the contract": the body stops restating what lives in the artifact.
- Design principle "Receipts are the portable product boundary" and the track "flow-swarm preparation (contract pillars SHIPPED)": new fields are additive, the version and path hold, and no reader depends on the body text.
- Design principle "Remember the bitter lesson": body sections that existed to steer a reviewer's attention are replaced by one general rule, and the instruction text that governed them is deleted.
- Key metric "Idea-to-merge wall-clock": with the sibling input spec's baseline, R11 gives make-pr three measured points.
