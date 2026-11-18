---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-333-review-model-registry-for-gpt-62-and.1 Implement Review model registry for GPT-6.2 and Fable 5.2, Fable only when pinned

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Review registry moves to GPT-6.2 Sol (codex, copilot) at medium and Opus 5.5 (claude) at high. Fable and gpt-6.2-astra sit in a per-backend `pinned_only` list: accepted without the unknown-model warning, never a ranking top or a ladder rung. The codex ChatGPT-account and copilot 1.0.114 unavailable texts now step the ladder; copilot quota, sign-in and other quoted-name failures do not. Legacy dash composites of pinned-only models still degrade to the bare backend. Docs: flowctl reference, troubleshooting, reach pages, setup review question, changelog. Codex scout baselines unchanged.

Tests: failing tests committed first (1b14c6d05); focused suites test_backend_spec, test_model_resolution and the review callers green; full suite 4475 tests, 0 failures; ruff clean. Live: bare codex ran gpt-6.2-sol at medium, bare claude ran claude-opus-5-5, pinned claude-fable-5-2 and gpt-6.2-astra ran with no warning, and the real codex ChatGPT-account text stepped the ladder (base 9.15 failed the same run).

stage: impl-review - ran [round 1 NEEDS_WORK (2 P1, 3 P2, 1 FYI; fixed 4, declined 1 + FYI); round 2 NEEDS_WORK (1 P1, the declined floor finding)] (model: gpt-6.2-sol)

OPEN_ITEM: The terminal floor (codex and claude omit --model, copilot uses auto) runs whatever the CLI itself defaults to; when every named rung is unavailable and the CLI is configured to default to Fable or GPT-6.2 Astra, a bare backend runs it. Removing or filtering the fn-76 never-fail floor changes existing floor assertions outside this spec; the person decides whether to do it.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 1b14c6d0528c0ef64f5f525e03bffc2d15661b67, 7f6776b4182a909aaf1ca8c95bf0835a9c485b2f, caff7552f3c4ecd2286c93b2f9be7c704d8b8631
- Tests: python3 scripts/run_tests_parallel.py
- PRs: