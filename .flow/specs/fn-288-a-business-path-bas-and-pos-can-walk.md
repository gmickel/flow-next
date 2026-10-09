# A business path BAs and POs can walk without engineering

## Goal & Context
<!-- Source: 10% user / 55% [paraphrase] / 35% [inferred] -->

Field feedback from a team adopting flow-next: engineers who own a change from requirement to delivery find the process easy, but business analysts and product owners, who own only part of it, find it too technical. They find the refine interview daunting, fall back to writing a requirements document (a BRD) and handing it over, and engineers end up running the requirements interview. That handover is where the requirement defects in that team's recent work came from. [paraphrase]

The maintainer's question: "is our product/business scope still too techniical". Mostly not in the questions themselves: refine already asks for plain words under a business lens, and the lighter-refine work keeps the question count low. The gaps are on the way in and around the questions. [paraphrase]

- Nothing tells a PO how to reach the business interview through `/flow-next:flow`, and flow's refine rule can skip refine when a PO asks to be interviewed. [paraphrase]
- Without a clear rule, a business-lens interview can still ask technical forks (data model, migration, public contract, security boundary). [inferred]
- "Not my call" counts as a skip and triggers one extra checkpoint question. [inferred]
- Refine's plain-words rule covers its questions, not its summary and read-back. [inferred]
- Starting from a BRD already works (paste it, point flow at it, or refine the file), but nothing tells a BA so. [paraphrase]

Target user: business analysts and product owners who author or refine the product side of a spec and hand the rest to engineering. [paraphrase]

## Architecture & Data Models

The fix is a few sentences in flow's routing, refine and the docs; it adds no flowctl verb, flag, config key, template section, label or validator (STRATEGY "Agent first"; this repo's SPEC.md rule). [paraphrase]

- **Flow routing** (the refine row and the plan-versus-no-plan refine rule): one sentence. [paraphrase]
- **Refine**: one sentence on technical forks under a non-technical lens, a change to the "not my call" answer shape, and widening the plain-words rule from questions to everything refine says under a non-technical lens. [inferred]
- **Docs**: a short BA/PO path in the teams guide, plus one line on the flow page. [paraphrase]
- The Codex mirror and the flow-next.dev pages follow through the usual sync and downstream chain. [inferred]

## Edge Cases & Constraints

- Some tests pin the flow routing and refine doc text; where a pinned string changes, the test changes with it. [inferred]
- Public docs and the spec body name no client, team or person; the feedback is described generically. [inferred]
- Unlensed refine and the technical-lens interview keep their current behaviour. [inferred]

## Acceptance Criteria

- **R1:** When the person tells `/flow-next:flow` their role or audience (for example "I'm the product owner", `--biz`, or `--scope=qa`) and flow routes to refine, refine runs with that lens: `--biz` for product or business, otherwise `--scope=<their words>`. An explicit request to be interviewed on a spec is enough reason to route to refine. Refine's existing test still decides what gets asked, and asking nothing remains a valid result. Errors: no stated role means flow behaves as today; under `--auto` refine stays outside the stage set and nothing changes. [paraphrase]
- **R2:** The teams guide has a short step-by-step path for BAs and POs. Start from a conversation or a BRD (paste it, point `/flow-next:flow` at it, or run refine on the file), then capture, then refine with the business lens, then hand the spec link to the tech lead. The flow docs say in one line how to reach the business interview through `/flow-next:flow`. No error surface beyond docs accuracy. [paraphrase]
- **R3:** Under a non-technical lens, refine does not ask technical forks (data model, migration, public contract, security boundary, external interface). The exception is when the answerer owns the consequence; then it asks about that consequence in their words (for example "existing customers' exports would change format: acceptable?"). Forks not asked are left to the technical pass and planning, with no extra spec entries. No error surface beyond R4. [inferred]
- **R4:** Under any lens, a "not my call" answer parks the question under `## Open Questions` with the other owner (engineering or product). It does not count as a skip, so it does not trigger the skipped-items checkpoint. Errors: a dismissal, "skip" or "I don't know" keeps today's skip handling. [inferred]
- **R5:** Under a non-technical lens, refine's plain-words rule covers everything it says to the person (round openers, read-back and completion summary), not only its questions. Internal terms such as source tags, criterion ids, section names and command names are glossed or left out. The read-back's approval options and write behaviour are unchanged. No error surface beyond today's read-back flow. [inferred]
- **R6:** The Codex mirror is synced and the affected tests pass. No change adds a question, option, checkpoint, flowctl verb, flag, config key, template section, fixed label or validator. No error surface. [paraphrase]

## Boundaries

- No change to capture: BRD intake already works and only needs documenting. [paraphrase]
- No change to the bundled spec template; teams that want business sections add them through a repo-root SPEC.md. [inferred]
- No role detection and no BA mode; the lens stays free text and the agent interprets it. [inferred]
- No change to unlensed refine or the technical-lens interview. [inferred]
- No change to doc-aware prompts (glossary, strategy) under a business lens; revisit only if field feedback shows they add questions for BAs and POs. [inferred]

## Decision Context

### Motivation

When BAs and POs retreat to a requirements document, engineers run the requirements interview and requirement defects follow. The fix keeps one interview and one spec file, the symmetric-interview pattern, and makes the product side's pass shorter and plainer. It adds no new questions anywhere. [paraphrase]

Each change is aimed at the business pass: R3 removes technical questions from it, R4 removes the skip checkpoint for "not my call", R1 and R2 make it reachable, and R5 only changes wording. [paraphrase]

Rejected: a separate BA mode, a business-only template, a standard "engineering decides" option on every question (it adds an option the trimmed question set rarely needs), capture changes for BRD intake (already works), and an "empty technical sections are engineering's" rule (nothing in refine or capture calls them incomplete today). [paraphrase]

Some of the field feedback is still to come; a refine pass can fold it in. [inferred]

## Strategy Alignment

Serves "Spec-driven team patterns" (the symmetric interview and the PO-to-tech-lead handover in the teams guide) and "Agent first" (guidance for the interviewer, no new structure). [strategy:Spec-driven team patterns]

## Strategy Conflicts

None found.
