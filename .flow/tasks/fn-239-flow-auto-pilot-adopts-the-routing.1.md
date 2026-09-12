---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14]
---
# fn-239-flow-auto-pilot-adopts-the-routing.1 Implement flow --auto: pilot adopts the routing reference and runs long-horizon over the same rails

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
First-frame evidence now captures the render-thread swap against the original launch clock and delivers the captured timestamp to the GUI journal. Commit 9c31b0c3 includes a regression that failed with queued capture and passed with direct capture; eight pacing checks passed.

R2 remains blocked on the unchanged native cold memory limits. The final production reference measured launch 1 at RSS 278064 KiB and anonymous memory 105412 KiB, exceeding the caps by 15920 KiB and 7108 KiB. The other native memory samples passed. All native first frames passed at 237, 210, 226, 210 and 218 ms. All five Xvfb launches passed; maxima were RSS 229736 KiB, anonymous memory 83132 KiB and first frame 232 ms. The route drive passed at 249 ms and live theme application at 7 ms.

The final exact mise exec just@1.58.0 -- just build test lint gate passed, with 1000 Cargo tests and 78 CTest entries. The initial gate's docs self-test failure and focused repair are retained. No allocator trim, shader-compiler release, renderer override, cache prewarming, scale change or threshold adjustment remains in production. Earlier failures and unrelated visual/installed-session acceptance remain unchanged.

The complete report is docs/reports/qa/2026-09-10-desktop-memory.md and its 2026-09-12-desktop-memory-diagnostics.json companion. Raw final command receipts are /tmp/fn55-clock-final/commands.json; the successful full gate log is /tmp/fn55-clock-canonical-final.log.

baseline: no Quick commands defined in the spec; conductor's pre-edit build passed, and the native reference failed before edits.
stage: impl-review - skipped(config: REVIEW_MODE=none)

BLOCKED: EXTERNAL_BLOCKED
Task: fn-55-desktop-memory-budgets-grounded-in.1
Summary: Native cold memory still exceeds the current reference caps after two rejected cleanup experiments.
Impact: fn-55 completion and release memory acceptance remain blocked.
Suggested resolution: Resolve the reference-contract or further-optimization decision; preserve current caps until Gordon explicitly changes the contract.
## Evidence
- Commits: 8ebb5974c7635d09e9166320fd80adb0037aac2f, 70ffa797a694667d8092ce7feb006fafa0896866, 212f84aec61377899ec199f2f85b07e22be7474d
- Tests: baseline: no Quick commands defined; pre-edit release build passed and native reference failed, python3 scripts/run_tests_parallel.py (verify after review round 1: 4888 ran, 0 failures, 6 skipped; green receipts for 8ebb5974 and the review-fix commit), QT_QPA_PLATFORM=offscreen build/qt/host/pacing/dettivo-pacing-test (8 passed; /tmp/fn55-first-frame-green.log), mise exec just@1.58.0 -- just build test lint (initial exit 1: unstaged evidence omitted from docs self-test copy; /tmp/fn55-clock-canonical-gate.log), mise exec just@1.58.0 -- just docs (repair exit 0; /tmp/fn55-clock-docs-retry.log), mise exec just@1.58.0 -- just build test lint (final exit 0; 1000 Cargo tests, 78 CTest entries; /tmp/fn55-clock-canonical-final.log), app_memory.wayland release reference (exit 1; launch 1 RSS 278064 KiB, anonymous 105412 KiB; all first frames pass; /tmp/fn55-clock-final/wayland), app_memory.xvfb release reference (exit 0; five launches; /tmp/fn55-clock-final/xvfb), DETTIVO_TIMING_GATE=1 app_routes (exit 0; first frame 249 ms; /tmp/fn55-clock-final/routes), DETTIVO_TIMING_GATE=1 app_theme_live (exit 0; theme 7 ms; /tmp/fn55-clock-final/theme), scripts/check-docs.sh (final report exit 0; /tmp/fn55-clock-final-docs-check.log), review round 1 (Codex, NEEDS_WORK, nine items) applied in the fix commit; sync-codex.sh x2 no diff; schema --check current; ruff clean
- PRs: