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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
