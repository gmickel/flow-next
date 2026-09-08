---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-236-scoped-review-execution-provider.1 Integrate and verify installed scoped review execution

## Description
Inspect and integrate development commits b9313d5a and 4348268f onto the current baseline. Preserve ordinary standalone behavior; generic hook, managed-required fail-closed behavior, installer completeness and semantic regressions. No new cloud architecture or MF workflow rules.

**Touches:** [plugins/flow-next/scripts/**, plugins/flow-next/tests/**, plugins/flow-next/docs/orchestration.md, plugins/flow-next/docs/flowctl.md, plugins/flow-next/codex/**, CHANGELOG.md, scripts/**]

Quick commands: python3 -m unittest discover -s plugins/flow-next/tests -p test_managed_review_execution.py; python3 scripts/gen_tracker_manifest.py; ./scripts/sync-codex.sh twice; python3 scripts/run_tests_parallel.py; uvx ruff@0.16.0 check .; git diff --check. Keep installs in disposable private test directories, never current user profiles.

## Acceptance
R1-R5 pass with ordinary CLI behavior preserved, installed launcher execution and failure coverage. Root conductor owns final real MF integration, docs-site and publication decisions.

## Done summary
Added generic scoped local review execution for all four packaged backends while preserving standalone CLI behavior and Flow-Next receipt ownership. Installed launcher, transport confidentiality/deadline/framing regressions and a real managed cockpit plan-review continuation passed; implementation review returned SHIP, 4,837 Python tests and required gates passed, and matching docs-site validation passed.

Plan-sync: skipped (planSync.enabled=false).
## Evidence
- Commits: c1eceb5f, 9774c656, ad086ddf401af8c19909fedaa51e425f9620588e, 2c708b722b65d878009b9819ba3ca2f22ad9b4d1, 88bdc5818ca39a46cc135bd609ceb0337cc1e2e5, a5a24f9a4f22d3e430731dc56a2c6308b78f9429
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p test_claude_review_commands.py, python3 -m unittest discover -s plugins/flow-next/tests -p test_managed_review_execution.py, python3 scripts/gen_tracker_manifest.py, ./scripts/sync-codex.sh (consecutive final outputs compared byte-identical), python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., python3 scripts/check_doc_anchors.py, flowctl validate --spec fn-236-scoped-review-execution-provider --json, git diff --check, flowctl codex impl-review fn-236-scoped-review-execution-provider.1 --base d35b4d9b --receipt /tmp/impl-review-receipt-b6b241c3cad1-fn-236-scoped-review-execution-provider.1.json --json (SHIP), Conductor installed cockpit Review plan -> /flow-next:plan-review fn-1-installed-review-upgrade-fixture (NEEDS_WORK -> SHIP with same managed reviewer session; all 12 structured checks pass; installation source a5a24f9a), Conductor installed implementation review (real NEEDS_WORK receipt with exact base/head correlation), Conductor docs-site docs/managed-review-integration: build, 4 tests, links and SEO pass twice
- PRs: