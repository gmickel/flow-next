---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-348-plan-runs-only-on-a-persons-ask-or.1 Implement Plan runs only on a person's ask or flow's route

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Setup snippets (Claude, Codex AGENTS.md) and the Cursor rule no longer say to run plan after creating a spec; a new line sends building, implementing or delivering a spec through flow-next-flow and keeps plan for a person's ask or flow's route (study arm B wording). The plan skill description is the study's C2 wording (quoted for YAML); Codex gets a 198-char catalog line and a new openai.yaml card. `flowctl next` sends a ready zero-task spec to `work <id> needs_implicit_task` (regression test first). map.sh drops plan from Next steps; teams, orchestration, pipeline-variations, running-lean and flowctl docs describe plan as a person's ask; troubleshooting and setup notes say to re-run setup when the changelog says the snippet changed. Work's unattended zero-task stop names the direct route and flow first. Changelog opens the Unreleased section. Conduct checklists for setup, plan and work updated. Codex mirror regenerated.

stage: impl-review - ran (model: gpt-6.2-sol) - round 1 NEEDS_WORK (3-lens panel), round 2 SHIP; Declined #4: sync-codex guard table phrase pin is the table's existing shape.

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: bb99d9be76154844f8fd7b69332761325200d7f5, 7374d9092cd5479c30ab1810410f65ab3f33172d, 4b8e409fcc52544f5c90d73bb952de586be81633, 5b768cdbc88bc4546ada7c06f40aafa3b748f741, 9c1bed18997520e526bdf467855f2072fee17732
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, plugins/flow-next/scripts/ci_test.sh, plugins/flow-next/scripts/map_smoke_test.sh
- PRs: