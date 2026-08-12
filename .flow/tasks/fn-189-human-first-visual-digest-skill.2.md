---
satisfies: [R4]
---
# fn-189-human-first-visual-digest-skill.2 Closer offers in capture, plan, interview

## Description
Add exactly ONE suggested-next-step line to each closer: flow-next-capture (after spec write-back, alongside its existing next-command suggestions), flow-next-plan (after task creation read-back), flow-next-interview (after final write). Shape: an offer naming `/flow-next:visual <spec-id>` as the fast way to review the result at a glance - phrased as an option, NEVER auto-run, no gate/probe machinery (unconditional one-liner). Find each skill's existing closing/next-steps block and append there; match surrounding prose style. Run sync-codex after (final task re-runs it too).

## Acceptance
R4: exactly one offer line per skill in the closing block; grep confirms no auto-invocation wording; token cost ~1 line each.

## Done summary
Added exactly one `/flow-next:visual` offer line to each of the three closers: capture's Phase 6 `Next:` footer block, plan's Step 8 (under the spec summary, unconditional, before the interactivity route), and interview's "Suggest next step" list. All three are phrased as options the user picks; no auto-invocation wording, no gate/probe machinery. Codex mirror regenerated for the three edited skills.

Notes: `./scripts/sync-codex.sh` (run twice, idempotent file set) exits 1 on a single pre-existing validation error - `flow-next-visual has no explicit allow_implicit_invocation` - which belongs to task .4 (REQUIRED_OPENAI_YAML_SKILLS / generate_openai_yaml); per conductor instruction that integration was NOT added here. The sync did write the mirror for this task's files, so the mirror is committed. The commit also carries the untracked codex mirror copy of task .1's visual skill (byproduct of the sync) and task .1's uncommitted `.flow/tasks/...1.md` done-summary, swept in by `git add -A`.

baseline: green (focused suite at pre-edit HEAD). Full suite is red with ONE inherited failure (test_chart_docs_inventory skill-count pin, caused by task .1's new skill dir at base commit cf3ada96) - task .4's listing-surface work closes it.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)
## Evidence
- Commits: f112340013f0023538c937bab1c07b22a4d8feef
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_command_shim_flatten -q (PASS; test_visual_skill not yet authored - task .5), ./scripts/sync-codex.sh x2 (mirror written + idempotent; 1 validation error, pre-existing: flow-next-visual openai.yaml integration owned by task .4), python3 scripts/run_tests_parallel.py (1 inherited failure: test_chart_docs_inventory skill-count pin 30!=29, caused by task .1's new skill dir at base commit cf3ada96; all other files pass)
- PRs:
stage: plan-sync - ran (no drift; task .4 enriched with test_chart_docs_inventory count-pin surfaces)
