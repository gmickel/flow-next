---
satisfies: [R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12]
---
# fn-309-decided-audit-changes-each-with-its.1 Implement Decided audit changes, each with its test (audit 2026-10 wave 3)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Audit wave 3: the decided changes, each with its check. Comparison records live in the eval
repository (studies/audit-wave3-2026-10).

- R1: NOT SHIPPED. The grouped must-ask screen failed its preregistered rule: F2 contradicted twice, and the amended-answer addendum tied. Reverted; capture keeps one question per turn. Open for the maintainer.
- R2: work's inline single-task path reads task and spec bodies once, through anchor. In the screen, A read them twice and B once, with the same outcome (done, 6/6 tests, same evidence shape).
- R3: plan review checkpoints before every dispatch and reads the spec only in the fix loop, editing it in place with targeted edits. M fixture: hand-edit marker survived A 3/3, B 2/3 (one heredoc rewrite), C 3/3 after the hardening. Verdicts match.
- R4: compared the emitter with the host check on four repos (monorepo, app, library, no template). DE1 verdicts agreed 4/4, but the review reproduced semantic gaps (members pooled, docs counted). DE4 disagreed on the monorepo (package.json scripts pooled). Both stay host-graded; the criterion map now says so.
- R5: resolve-pr refuses another repository's PR or comment URL before any fetch (fence test, bash and zsh).
- R6: the resolver returns one verdict per thread, clusters included; collection is per thread. Fence test: two-thread cluster gets two replies and two resolutions. Also fixed the reply loop exiting 1 when the last verdict is needs-human. A live run on a PR with a real two-thread cluster was not done.
- R7: rp/export notices removed from impl-review, plan-review, completion review, work, setup and plan. Smokes: typed --review=rp and a config holding rp both stop with flowctl naming the backends.
- R8: clawpatch range widened to >=0.4.0 <0.9.0, held only in map.sh. A real map run with clawpatch 0.8.4 on a fixture repo mapped 5 features; flowctl repo-map read them.
- R9: flow --auto treats --research (both spellings, value dropped) and --dry-run as unknown flags.
- R10: prime templates pin pre-commit-hooks v6.0.0, ruff-pre-commit v0.17.3 (hook id ruff-check, since ruff is now a legacy alias), Biome schema 2.6.4, actions/checkout v7; hooks-vs-CI note dropped. Checked with pre-commit validate-config and run, Biome 2.6.4 and actionlint.
- R11: memory-migrate runs as autofix under mode:autonomous / FLOW_AUTONOMOUS / AUTONOMOUS (fence test; smoke: no question, 3 entries migrated, originals untouched).
- R12: the template's customization guide is one pointer to flow-next.dev's scaffold guide, which already carries the text; skeleton output 9,561 to 8,281 bytes. A capture smoke writes the same sections as main.

stage: impl-review - ran (model: gpt-6.1-sol) — round 1 NEEDS_WORK (R4 DE1 semantics, R9 split-form value), fixed in 6620e10a, round 2 SHIP

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 8929b9fdf6f74e252792a7c75217a1132fde26d5, e8326c194c830d1ba8b4237fc67d1a9807084c00, 6620e10ad70b6248882c88a4043b7a58761509b3
- Tests: python3 scripts/run_tests_parallel.py (4088 OK at e8326c19); focused after fixes: tests.test_flow_auto tests.test_unattended_skill_fences tests.test_arg_loop_zsh; bash plugins/flow-next/scripts/map_smoke_test.sh; uvx ruff@0.16.0 check .; eval: agent-evals studies/audit-wave3-2026-10
- PRs: