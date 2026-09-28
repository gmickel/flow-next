# Agent-first sweep: defect route stops and feature-map plumbing

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 10% [user], 50% [paraphrase], 40% [inferred] -->

An audit on 2026-09-28 checked the recent specs against STRATEGY.md "Agent first" and pstack's playbooks. Nothing shipped repeats fn-265's form-before-acting failure, but two shipped surfaces carry more ceremony than the agent needs. The maintainer was unsure about these "mild ones" and asked for a follow-up spec. [paraphrase]

Target user: anyone running bug fixes or live-app stages through flow, attended or unattended. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

- **Defect route stops.** The prior-fix step stops and lists them when several open PRs plausibly touch the area. On a busy file that is a needless `NEEDS_HUMAN` unattended. The agent notes those PRs in the record and continues, stopping only when one of them actually fixes the bug or someone visibly owns a fix in progress. The reproduction step asks for a reproduction that fires reliably, as pstack's bug-fix playbook does, instead of a fixed "twice". [paraphrase]
- **Feature-map resolved-feature plumbing.** Stages carry the matched feature forward through an exact-key record: `flowctl done --resolved-feature`, the QA receipt's `resolved_feature`, a first-current-record precedence rule, the make-pr "Resolved feature" proof cell, and an intake step that confirms the spec shows the match verbatim. It exists so later stages need not re-find the feature. The 6.3.0 measurement shows reading the map costs 0 to 3 turns when the target is named, and the 2026-09-26 feature-map study found the rich fields and helper added nothing. Each stage reads the map and matches the feature itself; the plumbing and its tests are deleted. The feature files, drift notes and `flowctl features status` stay. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The defect route's prior-fix step continues past open PRs that touch the area, recording them, and stops only when one fixes the bug or a person visibly owns a fix in progress. [paraphrase]
- **R2:** The defect route asks for a reproduction that fires reliably, with no fixed repeat count. [paraphrase]
- **R3:** The resolved-feature record, its `flowctl done` flag, the QA receipt field, the precedence rule, the verbatim-confirmation intake step and the PR briefing's "Resolved feature" cell are removed with their tests; live-app stages match the feature from the map themselves. [paraphrase]
- **R4:** Existing receipts and task files that carry a `resolved_feature` value still load (the field is ignored). [inferred]
- **R5:** The docs and flow-next.dev pages that describe these behaviours match, and the full suite passes. [inferred]

## Boundaries
<!-- scope: business -->

- The feature files, their contract, drift notes, `flowctl features status` and `/flow-next:features` are unchanged. [inferred]
- No new mechanism replaces the removed ones. [paraphrase]

## Parked unknowns

- Flow's prototype-before-ask reference carries a judge fork-gate fence. It predates this batch and was not audited; look at it when this spec is picked up and fold it in only if it fails the agent-first test.

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

"agentic first, don't overengineer machinery"; "not sure about the mild ones, capture a followup spec". [user] As models improve, the right amount of machinery goes down; each removed stop and record is one less thing every run pays for. [paraphrase]

Left unready on purpose: the maintainer decides whether to run it.

## Strategy Alignment

Serves "Agent first" and "Remember the bitter lesson": deletes machinery the agent no longer needs.

## Strategy Conflicts

None found.
