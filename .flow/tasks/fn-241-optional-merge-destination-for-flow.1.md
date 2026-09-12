---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-241-optional-merge-destination-for-flow.1 Implement Optional merge destination for flow

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Flow now accepts `--until=merge` in attended and unattended runs and composes one selected spec/PR through land. Default unattended behavior stops before merge; attended existing-PR flow offers landing and requires current scoped consent.

Land keeps its gates, repair budgets and post-merge tail. The scoped handoff preserves PR-current Flow evidence in the source checkout, reads trusted configuration and runs the merge-verdict gate on the base, and reports merge success separately from closure/persistence. Scoped persistence failures retain local commits for recovery, including already closed specs.

Acceptance evidence:
- R1/R2: exact destination parsing rejects malformed values and clears inherited scope inputs. The routing smoke covers approval, decline, no answer, default behavior, and historical-consent refusal.
- R3: flow dispatches land as its only driver-composition exception. Existing pilot/land gates remain; the two-worktree test runs the actual merge-verdict fence on base while reading PR-only tasks/spec from source, with a conflicting feature-branch command as the negative control.
- R4: executable outcome mapping covers tick/continuation, external waits, progress, blockers and false completion. The smoke records three land ticks with two cadence waits and no pilot strike.
- R5: executable candidate and PR probes exclude unrelated specs/PRs, allow closed-spec tail recovery and reject missing identity, lost authority, wrong/absent/dirty base workspaces and failed status reads. Checkout/pull failure keeps the tail disabled.
- R6: current consent survives authorized waits and revocation stops further dispatch. Merge observation recognizes a confirmed merge after a command error; empty close commits are avoided, and a failed required tail never reports completion. The smoke exercises revoked consent and partial merged-tail recovery.
- R7: 324 focused tests passed, including 9 new executable tests. The 9 new tests also passed from the installed Codex layout. Final mirror regeneration was byte-idempotent; scratch Codex and OpenCode installations preserved all flow/land files. Repository docs, commands, conduct checklists, glossary, changelog and generated mirrors are aligned.

baseline: none (the parent spec defines no Quick commands). Additional pre-edit pilot baseline was green: 95 tests. Initial failing reproductions are retained under `.flow/tmp/fn241-*-red.log`; current test logs are `.flow/tmp/fn241-verify-*.log`, `.flow/tmp/fn241-final-*.log`, and `.flow/tmp/fn241-installed-tests.log`.

The Astra high screen passed 12/12 frozen synthetic routing cases. Its stage/GitHub observations were simulated; it does not establish a live merge, measured behavioral improvement, cross-host enforcement, or MergeFoundry integration. Reproduction and trace artifacts are under `.flow/tmp/fn241-smoke/`. Executable fence tests cover the final code, including the later inherited-input reset and workspace-status failure guard.

The conductor ran the final FULL gate on f1d91c139f7e88da9c385707ed6a7582be38eb8d: python3 scripts/run_tests_parallel.py passed 4,895 tests across 214 files (zero failures/errors; six skips), and uvx ruff@0.16.0 check . passed. Both green receipts were recorded. Downstream documentation is prepared and committed on local companion branches; publication, version/release entries, and the vault release ceremony remain in the separate release handoff.

G1: the added always-loaded parser encodes the destination boundary; the longer consent/continuation rule and source/base checks are disclosed only at the PR boundary or scoped land handoff. No public selector, consent store, scheduler or new CLI helper was added.

stage: impl-review - skipped(policy: user requested PR Bugbot instead of local model review)
stage: completion-review - skipped(policy: user requested PR Bugbot instead of local model review; no verdict claimed)
stage: plan-sync - skipped(config: planSync.enabled != true)

stage: qa - skipped(config: pipeline.qa=off)
stage: quality-auditor - skipped(policy: user requested PR Bugbot instead of local model review)

Release follow-up: Bugbot found a wrong-source-branch fast-forward and unrewritten actionable Codex dispatches. Both are fixed with actual Git and generator/installed-consumer regressions; the macOS physical-path expectation is corrected. The combined 5.2.0 candidate passed python3 scripts/run_tests_parallel.py: 4,899 tests, 215 files, zero failures/errors, six skips. Ruff and anchor checks passed, and regenerated mirrors were byte-idempotent. New GitHub CI and Bugbot verification remain required before merge/tag.
## Evidence
- Commits: 94fb6ac968309809c65752e66f2bf31688f98465, f1d91c139f7e88da9c385707ed6a7582be38eb8d, f2dec4c8b02b414ff8c9dedef7462614afa4678b, 178432581637f351a82f5f78b27ec645651fa196
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_pilot*.py', python3 -m unittest discover -s plugins/flow-next/tests -p 'test_land*.py', python3 -m unittest discover -s plugins/flow-next/tests -p 'test_flow_merge_destination.py', python3 -m unittest discover -s plugins/flow-next/tests -p 'test_skill_prose_diet.py', python3 -m unittest discover -s plugins/flow-next/tests -p 'test_flow_config_schema.py', python3 -m unittest discover -s plugins/flow-next/tests -p 'test_flow_auto.py', python3 -m unittest discover -s plugins/flow-next/tests -p 'test_flow_routing.py', python3 -m unittest discover -s plugins/flow-next/tests -p 'test_flow_config_schema_drift.py', python3 .flow/tmp/fn241-smoke/score.py (12/12 synthetic routing cases; one Astra high screen), ./scripts/sync-codex.sh (two final passes; byte-identical generated tree), env CODEX_HOME="$PWD/.flow/tmp/fn241-installed-codex" ./scripts/install-codex.sh (scratch consumer), ./scripts/install-opencode.sh --dest "$PWD/.flow/tmp/fn241-installed-opencode", test_flow_merge_destination.py against installed Codex PLUGIN root (9 tests), Installed flow/land file parity: Codex 16 files, OpenCode 14 files, git diff --check, python3 scripts/run_tests_parallel.py: 4895 tests, 214 files, zero failures/errors, 6 skips (f1d91c13), uvx ruff@0.16.0 check .: passed (f1d91c13), flowctl validate --spec fn-241 --json: valid, zero errors/warnings, Release candidate: python3 scripts/run_tests_parallel.py — 4899 tests, 215 files, zero failures/errors, six skips, Release candidate: uvx ruff@0.16.0 check . — passed, Wrong-source-branch actual Git matrix: nine scenarios, all pass; includes correct fast-forward, same-SHA wrong branch, detached and merged recovery, Codex dispatch generator/installed consumer: three tests pass; malformed invocation and missing target are rejected
- PRs: