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
Every Haiku/Sonnet-pinned bundled agent (all scouts, flow-gap-analyst, plan-sync) now pins `opus`. The Codex mirror baselines moved to gpt-6-sol (intelligent) and gpt-6-luna (fast), and the mirror was regenerated. The codex triage judge now defaults to gpt-6-luna; copilot stays on claude-haiku-4.5. gpt-6-sol now follows gpt-6-astra in the codex ranking. Resumed codex reviews (re-review, validator, deep pass) now re-pin the model recorded in the prior receipt (#486); when that model is unknown or is the floor's "default", nothing is pinned. Tests: test_review_convergence_cap TestCodexResumeArgvParity (argv for a known model, the floor, and an unknown model, plus validator/deep plumbing); test_backend_spec R4 ranking; test_model_resolution judge baseline. Docs updated: orchestration.md, platforms.md, CHANGELOG Unreleased (credits @TechupBusiness). The flow-next.dev changes are committed locally as b09b396 on branch fn-272-scout-model-pins-opus-on-claude-gpt-6 in ~/work/flow-next.dev-fn-272 and are not pushed.

Follow-ups, not built:
- The managed review-execution path (FLOW_REVIEW_EXECUTION_URL, execute_review) still sends spec.model on resume. This predates the change and was flagged by review as a pre-existing P2.
- flow-next.dev model-routing.mdx says unset tiers stay on the session model, but scouts actually use their agent default. This was already inexact before this change.
- platforms.md says "20 agents"; the mirror has 21.

baseline: green (python3 scripts/run_tests_parallel.py, pre-edit, 5235 tests)

stage: impl-review - ran (codex gpt-6-astra high, fan-out 3/3 SHIP, round 1)

Tier: session - explicit override: implementer opus 5.5 (actual: claude-opus-5-5)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 52fffc073c9edde4f48f1ab0e4e40ed271bd3120
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: