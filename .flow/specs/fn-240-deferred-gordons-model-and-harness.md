# Deferred: Gordon's model and harness recommendations

## Goal & Context

**Deferred by Gordon on 2026-09-13. Keep this spec open, unready, and without implementation tasks.** [user]

Users can already choose models, harnesses, effort, and role assignments through the orchestration block Flow-Next provides. There is no immediate need to add another mechanism for those choices. The existing block remains the way to express a bespoke routing policy. [paraphrase]

If this idea is revisited, the candidate is an optional, Gordon-authored recommendation based on his preferences and observed results. Discovering an installed harness or configured model does not by itself establish which one should implement a spec or whether review is necessary. Automatic selection of the primary implementer is no longer the proposed outcome. [paraphrase]

Gordon raised a possible complexity measure and the earlier intelligence/taste table as inputs to think about later. Their dimensions, evidence, maintenance, and usefulness remain unresolved; this deferral does not approve a scoring system or a routing table implementation. [paraphrase]

## Architecture & Data Models

- Existing orchestration preferences and explicit user routing remain authoritative. No new routing mechanism is selected or implemented in this spec update. [paraphrase]
- A future recommendation would explain which user-authored preference it applies. Limited automatic choices for simple work remain a possibility to assess, not an accepted implementation requirement. [paraphrase]
- Keep model/harness assignment separate from the policy deciding whether a review runs. Model rankings alone do not authorize changing review requirements. [paraphrase]
- The historical session-model probe was dropped during fn-238. Do not revive it through this deferred idea. [paraphrase]
- The proposed coupling between routed implementation and mandatory task decomposition is removed from this spec's intended architecture. Assess the shipped rule independently; no routing or decomposition behavior changes here. [user]

## Acceptance Criteria

This spec is deferred and none of these criteria authorizes execution. R1-R4 are retained verbatim for provenance. **R1 and R3 are superseded by the 2026-09-13 decision and are not requirements to implement.** R2 and R4 remain constraints for any future proposal. R5-R6 describe the narrowed candidate if Gordon explicitly resumes it.

- **R1:** Flow selects a harness and tier per stage from configured and installed reach, prints the choice once, and never overrides an explicit argument or a routing-block line. [paraphrase]
- **R2:** No model identity is inferred from the session. Unknown stays unknown and routes to the session model. [user]
- **R3:** The routed-out implementer signal flips the plan-versus-no-plan default for that spec and is recorded in the route decision. [paraphrase]
- **R4:** Host review keeps its fresh-context, read-only, cross-family contract and fails closed. [paraphrase]
- **R5:** Any resumed proposal starts from optional, bespoke Gordon-authored recommendations and explains what they add beyond the existing user-controlled orchestration block. [paraphrase]
- **R6:** Any resumed proposal keeps implementer selection, review necessity, and task decomposition as separate decisions; the idea of a complexity measure or intelligence/taste table remains a question to resolve before adopting it. [paraphrase]

## Boundaries

- No implementation, task creation, readiness promotion, release, or downstream product change now. Resume only on Gordon's explicit request. [user]
- No change to the existing orchestration block or review backend configuration grammar. [paraphrase]
- No autonomous model/harness selection, capability scorer, model registry, or session-model probe is approved. [paraphrase]
- No change to the shipped routed-implementer planning rule in this spec. The possible removal of that rule is separate work, not a dependency for deferring fn-240. [user]

## Decision Context

### Motivation

- Original sequence: deferred from fn-238 until fn-239 supplied the shared conductor. That sequencing reason is historical; the new deferral is a product decision even though fn-239 is complete. [paraphrase]
- 2026-09-13: Gordon questioned whether the model can reliably choose the implementation model/harness or decide when review is necessary. He suggested bespoke recommendations and possibly a complexity measure plus an intelligence/taste table. These are discussion inputs, not validated routing heuristics. [paraphrase]
- 2026-09-13: Gordon explicitly asked to update and defer the spec because users already have the orchestration block to make these choices themselves. Preserve that capability; do not treat the deferral as a rejection of user-authored routing. [user]

### Implementation Tradeoffs

- Separate question, recorded without creating another spec: does using a cross-harness implementer justify mandatory task decomposition? Gordon asked to consider removing that boundary independently and to finish this deferral first. No decision to remove the shipped rule has been made here. [user]

## Parked unknowns

- What practical gap would a packaged recommendation fill beyond the current orchestration block?
- Which recommendations would Gordon maintain, and what evidence would make them useful across model, effort, harness, and account differences?
- Would a complexity measure and an intelligence/taste table improve recommendations enough to justify their upkeep? No dimensions or scores are accepted yet.
- Which simple choices, if any, should a user be able to delegate automatically under an explicit policy?
