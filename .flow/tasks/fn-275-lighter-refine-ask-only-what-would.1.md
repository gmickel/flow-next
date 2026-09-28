---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9]
---
# fn-275-lighter-refine-ask-only-what-would.1 Implement Lighter refine: ask only what would change the build

## Description
Implement the parent spec in one pass (no-plan task). The spec is mostly deletion: lighten refine's question rules and banks, drop the pending-technical placeholder from the write policy, state the when-to-refine rule once in plan-vs-no-plan, stop the structured-brief and refine routing rows defaulting into refine (presentation text only; judge criteria text unchanged), point prospect at `/flow-next:flow <id>`, remove capture's sparse-business refine suggestion, and sync conduct checklists, docs, CHANGELOG and flow-next.dev pages.

Review focus (maintainer steering): overengineering, slop and YAGNI. Reject any added mechanism (question budget, detector, config key, check, new routing row) per G4; machinery the change makes unnecessary is deleted in the same change.
## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Refine now asks a question only when it passes one test (a wrong guess builds the wrong thing, nothing but the user can settle it, and it is their call), stops when none remain, treats zero questions as a valid outcome, and records answers at the precision given. The banks are short check-lists. The when-to-refine rule is stated once in plan-vs-no-plan.md, and the route-matrix and judge presentation skip cells point to it; the criteria text is unchanged. Prospect points at `/flow-next:flow`. Capture's R25 business-refine suggestion and its signal count are gone, and so is the pending-technical placeholder, including the `placeholder_write` and `tech_sections_have_content` write-policy surface. Conduct checklists, docs, GLOSSARY, CHANGELOG and the codex mirror are updated. The flow-next.dev pages are committed locally as aa272c5 on branch fn-275-lighter-refine-ask-only-what-would in ~/work/flow-next.dev-fn-275 (not pushed).

Removed with the topic banks: the technical bank's "Maintainability (ask once)" pair and its conduct item. Plan review keeps its maintainability criterion.

Judgment calls:
- R5: the refine row's positive-signal cell is part of the judge criteria text, so the named-decision requirement went into the skip cell instead.
- Survivors show `**Next step:** promote, then /flow-next:flow <spec-id>`, because a survivor has no id before promote.

A test-only follow-up commit (058d5613) came after the review SHIP at 5ce9d51d. It removed one assertion that anchored on the deleted capture section heading. The remaining count==1 and in-editor assertions still pin that instruction's placement.

Tests: removed the placeholder and R25 tests and added test_no_scope_emits_a_placeholder_write (R7).

Tier: session - explicit override: implementer opus 5.5

stage: impl-review - ran [2026-09-28T09:36Z..2026-09-28T09:40Z] (codex gpt-6-astra high, 3-draw fan-out, all SHIP, 0 findings)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 5ce9d51d31fcf8d1f85cfb9cb3f7f0d579a9b923, 058d5613ac88c7a24a136fcac7dc659e5453b890
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: