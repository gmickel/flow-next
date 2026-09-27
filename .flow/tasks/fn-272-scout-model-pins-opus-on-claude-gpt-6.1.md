---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-272-scout-model-pins-opus-on-claude-gpt-6.1 Implement Scout model pins: Opus on Claude, gpt-6 on Codex

## Description
Implement every R-ID of the parent spec in one change: move the Haiku/Sonnet agent pins to `opus`, bump the Codex mirror baselines (gpt-6-luna fast, gpt-6-sol intelligent) and regenerate the mirror, move the codex triage-judge baseline to gpt-6-luna (copilot stays claude-haiku-4.5), add gpt-6-sol after gpt-6-astra in the codex ranking, re-pin the original dispatch's model on every resumed codex review turn (issue #486), and update the docs, pins and CHANGELOG that name these defaults.

Review focus (maintainer steering): overengineering, slop and YAGNI. This spec changes default pins plus one resume fix only - flag any new routing mechanism, config key, model-selection logic, speculative guard, or test mass beyond one focused test per behaviour.
## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
