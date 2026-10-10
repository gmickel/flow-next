---
satisfies: [R15, R16, R17]
---
# fn-291-work-routes-and-records-an-explicitly.1 Implement work routes and records an explicitly named implementer

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
work's tier step (`judge_tier_dispatch`) now routes an explicit implementer ahead of any judge answer, with or without a Jev key: spawn_model when the host can spawn it, the bridge otherwise (also when a role pins the model), and a "Tier: session - explicit implementer <m> unreachable (...)" line when neither. The tier line names the model in every case. judge-tier.md, the worker's actual-model rule (the model its environment states counts as host evidence) and docs/judge.md now record `(model: not reported)` instead of nothing. Codex mirror regenerated; CHANGELOG Unreleased entry added.

Checked: test_judge_consumers.py failed on the old code (explicit model never reached spawn args) and passes after; real CLI with and without TYPESAFE_API_KEY for native spawn, bridge-only and no explicit model; full suite 216 files, 3996 tests, 0 failures; ruff and sync-codex --check clean.

stage: impl-review - ran (model: gpt-6-astra) SHIP, one reviewer, focus "overengineering, slop and YAGNI"

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 2deb04d506f5ce60ea1857da4c504918a5817197, 98460e4856c801b26ff71956e4a01f4712867b5d
- Tests: python3 scripts/run_tests_parallel.py
- PRs: