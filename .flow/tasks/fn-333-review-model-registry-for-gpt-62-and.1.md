---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8]
---
# fn-333-review-model-registry-for-gpt-62-and.1 Implement Review model registry for GPT-6.2 and Fable 5.2, Fable only when pinned

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Review registry moves to GPT-6.2 Sol (codex, copilot) at medium and Opus 5.5 (claude) at high. Fable and gpt-6.2-astra sit in a per-backend `pinned_only` list: accepted without the unknown-model warning, never a ranking top or a ladder rung. The fallback's last step runs the CLI's own configured default model (R2 as amended), and the docs say so. The codex ChatGPT-account and copilot 1.0.114 unavailable texts now step the ladder; copilot quota, sign-in and other quoted-name failures do not. Legacy dash composites of pinned-only models still degrade to the bare backend.

R8: the findings parser reads the GPT-6.2 layouts (colon-less labels, `·`-joined fields, severity tuple or heading, the prompt-column table, link anchors) for every review kind. Text in the prompt's layout parses as written; the rewritten reading wins only when the first fails or finds more findings, and it skips code fences. Reviewer study, 144 lenses: parsed 70 -> 144, each count equal to the findings the text holds, and the 70 previously parsed lenses (all 54 GPT-6.1 Sol) identical. Docs: flowctl reference, review-findings, troubleshooting, reach pages, setup review question, changelog.

Tests: failing tests committed first (1b14c6d05, fa8a945e6); focused suites green; full suite 4484 tests, 0 failures; ruff clean.

stage: impl-review - ran [rounds 1-2 on gpt-6.2-sol medium NEEDS_WORK (floor finding, later settled by the R2 amendment); rounds 3-5 on gpt-6.1-sol high: NEEDS_WORK (1 P1, 1 P2, fixed), NEEDS_WORK (1 P1, fixed), SHIP] (model: gpt-6.1-sol)

CI fix after SHIP: the layout rewrite returns unchanged text as-is, so a review in the prompt's layout is parsed once (Windows max-item budget: main 14 ms, previous head 29 ms, now 15.5 ms process time; 144-lens parity unchanged).

stage: impl-review - skipped(policy: risk - one-line behaviour-preserving fix after the round-5 SHIP; regression test and corpus parity)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 504ca520a4ecec2f22d00dcac6298c3a860a4a92, 1b14c6d0528c0ef64f5f525e03bffc2d15661b67, 7f6776b4182a909aaf1ca8c95bf0835a9c485b2f, caff7552f3c4ecd2286c93b2f9be7c704d8b8631, 9da09f90aca6c14d1ce25ada2395749e885bc636, 30d35295541257e9ef7108ba70a7bc52f0a673c2, 6314e4a175c540010509a0e4903aa2c76907b397, 2960a4d711d976145a4f709520a8d521518d17e3, 5c837421c8410b82388b632206408bc22d5be3ea, fa8a945e6481822d45a81911ad0f8a2512b0498a, fd241ff159ff5c1ff0f978ee6537125be08b685a, 849bdc86981b8d4877a16cdd663c9780cf2eb2e9, a645fe7fb9dfc5903d973948c3f4b2a15ca6c442, 2f61a9311f69b1b44dddea3bd61bd8b2ff9fbd17, 6efeba8dcdd69f4a90d3c8d4ac184a5f419ae242
- Tests: python3 scripts/run_tests_parallel.py
- PRs: