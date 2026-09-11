# Harness and model autorouting on top of flow

<!-- STUB. Sequenced after fn-239. Captured from the fn-238 discussion; refine with /flow-next:interview before work. -->

## Goal & Context
<!-- Goal & Context: 60% [user], 40% [paraphrase] -->

Once flow chooses the route, the remaining choice is who executes each stage. Flow-Next already discovers installed harnesses and configured backends (the review-backend ladder, the project routing block, the usage recipes, setup's host detection). This spec lets flow use that discovery to pick the harness and model tier per stage, opinionated by default, with explicit user routing and the routing block always winning.

A per-harness "current model" probe was smoke-tested during fn-238 and dropped. Only one harness exposes its live model and effort reliably; one exposes only its configured default; one exposes nothing. Autorouting therefore keys on what is configured and installed, never on a guess about the session model.

## Architecture & Data Models
<!-- Architecture & Data Models: 30% [user], 70% [paraphrase] -->

- Precedence is unchanged: explicit invocation argument, then the project routing block, then the agent definition's default, then the session model. Autorouting fills the tiers the routing block leaves unset.
- The plan-versus-no-plan rule's "implementer routed out" signal is the first consumer: when autorouting sends implementation to a cheaper tier, planning becomes the default for that spec.
- Review keeps its own cross-family requirement and fails closed when no independent reviewer is reachable.
- Unreachable preference falls back to the session model with one notice, as today.

## Acceptance Criteria

- **R1:** Flow selects a harness and tier per stage from configured and installed reach, prints the choice once, and never overrides an explicit argument or a routing-block line. [paraphrase]
- **R2:** No model identity is inferred from the session. Unknown stays unknown and routes to the session model. [user]
- **R3:** The routed-out implementer signal flips the plan-versus-no-plan default for that spec and is recorded in the route decision. [paraphrase]
- **R4:** Host review keeps its fresh-context, read-only, cross-family contract and fails closed. [paraphrase]

## Boundaries

- No model registry, no capability scorer, no session-model probe. [user]
- No change to review backend configuration grammar. [paraphrase]

## Decision Context

- Deferred from fn-238 because the pieces exist but the entry point that would use them does not yet. [user]
