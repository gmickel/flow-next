---
satisfies: [R3]
---
# fn-137-global-acceptance-criteria-object.3 Setup scaffold opt-in

## Description
Setup offers the criteria scaffold; declining leaves no trace.

**Size:** S

**Files:** setup skill prose (both canonical + sync-codex), a template criteria file (bundled), tests where setup artifacts are tested.

### Approach
- Setup gains an opt-in question (existing setup question conventions; AskUserQuestion canonical + numbered-prompt mirror) offering .flow/criteria.md scaffold; template documents the G-ID grammar with 2-3 commented examples.
- Respect setup-modes (copy vs plugin) per agent_docs/setup-modes.md resolution chains.

## Acceptance
- [ ] Opt-in scaffold w/ documented template; decline = no trace; both setup modes honored; sync-codex idempotent (R3).

## Done summary
Setup now offers an opt-in "Global criteria" question (6d grouped prompt, gated on .flow/criteria.md absence, both setup modes) that scaffolds .flow/criteria.md from a new bundled template documenting the G-ID grammar with 3 commented examples; declining writes nothing - no file, no config key, no meta stamp - and an existing file is never re-asked about or touched. Template parses clean via flowctl criteria list --json (0 active criteria), guarded by TestCriteriaTemplate; codex mirror regenerated (sync-codex x2 idempotent) and reached-path evidence refreshed. Template + test code delegated to grok-4.5 via the cursor-agent bridge; skill prose and review by the orchestrator.
## Evidence
- Commits: 2319b7b8de5b480c84775062be3e7eeb8db544b5, 364fe43a
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_criteria test_setup_snippet_lockstep test_setup_reference_routing test_setup_cursor_host test_setup_grok_host test_setup_mode_stamp test_template_canonical test_dogfood_template_parity test_rp_setup_workflow_contract test_prompt_text_pinned -q (123 tests OK; baseline green pre-edit on test_criteria), uvx ruff@0.16.0 check plugins/flow-next/tests/test_criteria.py plugins/flow-next/scripts/flowctl.py (clean), ./scripts/sync-codex.sh x2 (idempotent, exit 0 both runs), post-review: python3 -m unittest test_criteria test_setup_reference_routing -q (OK)
- PRs: