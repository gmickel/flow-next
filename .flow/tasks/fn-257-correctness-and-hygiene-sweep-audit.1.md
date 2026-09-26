---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23]
---
# fn-257-correctness-and-hygiene-sweep-audit.1 Implement Correctness and hygiene sweep (audit wave 3)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Implemented all 23 R-IDs of the correctness and hygiene sweep as small independent fixes across the review, planning, capture, memory, setup, prime and task skills and flowctl's done/block, error, pipe, lock and write paths; the interview and pilot command shims are removed and a shipped-link unit test guards installed-layout links.

Tier: session (jev long_running 0.61)

Deliberate narrowings: plan-review host receipts record `head` only (plan review binds no diff base); `SNIPPET_SCHEMA_VERSION` kept because agent docs cite it; `block` gained no assignee check (it would need a new `--force` flag); the pilot and interview skill stubs remain (R21 names only the command shims). Follow-ups outside scope: ralph-init and resolve-pr preambles lack the `<plugin-root>` rung; `save_task_runtime` is now test-only.

Error-case tests: R3 missing `--files` entry and R5 unresolvable base (test_claude_review_commands), R18 evidence keys and lock re-checks (test_done_block_ergonomics), R19 Windows retry bound, hints and closed pipe (test_done_block_ergonomics), R15 malformed frontmatter and unsupported values (test_memory_marks, test_memory_schema), R17 timeout finding (test_prime_run_bounded), R12 broken links (test_shipped_links).

stage: impl-review - ran (codex gpt-6-astra high; round 1 fan-out NEEDS_WORK with 4 findings fixed, round 2 SHIP)
stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 133036959e7731b2e4b6ce7818159bb954ae4ada, 1c3263578badb4ee8463f675a7ab66f5fac3512c, ac1a114cb99e18368690261b930539eaf0907b33
- Tests: python3 scripts/run_tests_parallel.py (baseline green 5081; final green 5111, 0 failures), uvx ruff@0.16.0 check ., python3 scripts/check_doc_anchors.py, ./scripts/sync-codex.sh (x2, idempotent), python3 scripts/gen_tracker_manifest.py, test_done_block_ergonomics.py, test_shipped_links.py, test_prime_run_bounded.py, test_capture_config_snapshot.py, test_task_skill_contract.py, test_memory_marks.py, test_memory_schema.py, test_host_review_backend.py, test_claude_review_commands.py
- PRs: