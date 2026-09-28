# Sharper handovers: shared assumption and safety fact

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 60% [paraphrase], 30% [inferred] -->

Two handovers carry most of the weight when an agent hands work back to a person: the stop when repeated attempts fail, and the PR briefing a reviewer reads first. Both could say more with the same effort. [paraphrase]

When two attempts fail the same gate, the handover says what failed but rarely why both failed. Often both assumed something that is not true. Naming that assumption and one alternative worth trying turns a dead stop into a useful next step. [paraphrase]

The PR briefing's blast-radius prose rarely says the one thing a reviewer most needs: which fact the change is safe because of, and how that fact was established (stated, pointed at in the code, run, reproduced). [paraphrase]

Both are judgment written as prose by the agent that has the context. This spec adds guidance, not structure. [paraphrase]

Target user: the human who receives a stop, and the reviewer who opens the PR. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

- **Shared assumption in escalations.** The worker's escalation guidance asks, when attempts at the same task have failed repeatedly, for one sentence naming the assumption the attempts shared and one alternative worth trying next, or saying they shared none. The stages that already relay the worker's escalation text (work's routes, and through them land, `flow --auto` and resolve-pr) carry it unchanged. No fixed labels, no verdict-grammar change, no new field. [paraphrase]
- **Safety fact in the briefing.** make-pr's guidance for the existing `blastRadius` prose asks for one sentence: the fact the change is safe because of, and how it was established. When no single fact carries the safety, it says so. The proof cells already mark what passed and what is unverified. No schema field, enum or validator change. [paraphrase]

### Worked example

Work fails the same task twice: attempt one added a retry around a flaky upload, attempt two raised the timeout, and both still fail the integration gate. The escalation adds: "Both attempts assumed the upload fails because the network is slow; both runs log a 413 on chunk 2, so check the test server's body-size limit next."

A schema-change PR's blast radius reads: "Safe because the new `archived_at` column is nullable and no existing query filters on it; I ran the migration on production-shaped data and the full query suite passed." Another reads: "Safe because only the CSV exporter calls `format_row` (one call site, pointed at, not run)."

## Acceptance Criteria
<!-- scope: both -->

- **R1:** After repeated failures of the same task, the worker's escalation includes one sentence naming the shared assumption and one alternative, or saying there was none; the existing relays carry it unchanged. [paraphrase]
- **R2:** make-pr's blast-radius prose names the fact the change is safe because of and how it was established, or says no single fact carries it. [paraphrase]
- **R3:** No schema field, enum, fixed label, validator rule, verdict-grammar change, cap, counter or reset rule is added or changed. [paraphrase]
- **R4:** The worker escalation and make-pr pages on flow-next.dev show one example each. [inferred]

## Boundaries
<!-- scope: business -->

- Guidance only: no new structure the agent must fill before it may act, per STRATEGY.md "Agent first". [paraphrase]
- No change to land, `flow --auto` or resolve-pr beyond relaying the worker's text as they already do. [paraphrase]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

Trimmed on 2026-09-28 before build. The first version added a `safetyBasis` briefing field with a six-level proof enum enforced by the validator and required on every briefing, and threaded fixed `Shared assumption:` / `Alternative:` labels through four verdict surfaces and their grammar tests. The maintainer's direction is agent first, without machinery ("agentic first, don't overengineer machinery"). [user] The same value lands as two sentences of guidance the agent writes in prose it already writes. [paraphrase]

Delivery order: 7 of the fn-261..fn-270 set; independent; route direct, `/flow-next:work fn-267-sharper-handovers-shared-assumption-and --no-plan`.

## Strategy Alignment

Serves "Agent first" and the approach line of reviewable handover objects: both handovers carry the reasoning a human needs, written by the agent that has it.

## Strategy Conflicts

None found.
