---
satisfies: [R8, R9]
---
# fn-189-human-first-visual-digest-skill.5 Conduct checklist + prose-contract tests + dogfood

## Description
(1) `agent_docs/conduct/visual.md`: 4-6 falsifiable transcript-checkable behaviors (digest fits one screen; every file-tree path exists in a task file, spec, or diff; no mermaid when a text shape sufficed; a prose sentence precedes every visual; coverage line matches `show --json` satisfies arrays; read-only - no writes). Index row in `agent_docs/conduct/README.md`. Never referenced from the skill's own files. (2) New `plugins/flow-next/tests/test_visual_skill.py` per the prose-contract heuristic (pin CONTENT + REACHABILITY, location only where load-bearing): shim bare name `name: visual`; description NL trigger phrases; all 8 vocabulary shapes present in the skill dir; the three closer offer lines (content in each skill + the line names /flow-next:visual); the make-pr sketch clause in its home file. (3) Dogfood once: run the skill against THIS spec post-plan in a real session; walk the conduct checklist, mark each item pass/fail in the task summary; fix prose that fails. (4) Final gate: focused suites + `./scripts/sync-codex.sh` twice + `uvx ruff@0.16.0 check .` (no flowctl.py changes expected, so no dual-copy/manifest steps - verify with git status).

## Acceptance
R8: conduct file + index row, transcript-checkable items only. R9: test file green, pins per heuristic. Dogfood transcript walked against conduct list with per-item pass/fail recorded in the task summary.

## Done summary
Added the `/flow-next:visual` conduct checklist (`agent_docs/conduct/visual.md`, 6 falsifiable transcript-checkable items + index row in `conduct/README.md`, never referenced from the skill's own files) and the prose-contract test `plugins/flow-next/tests/test_visual_skill.py` (pins the shim's bare colon-free `name: visual`, the description's NL trigger phrases + four targets, all 8 vocabulary shapes plus the five discipline rules, the three closer offers with reachability, the make-pr §8 sketch clause with Phase-3 reachability, and that no skill file points at the conduct doc). Pins are content/reachability only - no stored hashes, no size ceilings, no sentence-level assertions.

Dogfood (spec digest of fn-189 against the conduct list, all 6 items PASS): one-screen digest with the six ordered elements; every path traced to `git diff --stat`/task files; coverage line R1-R3 -> .1, R4 -> .2, R5 -> .3, R6/R7 -> .4, R8/R9 -> .5 (none uncovered); prose preceded each visual, 4 of 8 shapes used; no mermaid; read-only. Dogfood found one real defect and fixed it: the skill (and this checklist) told the agent to read `satisfies` from `show --json`, which does not carry that field - both now name each task file's frontmatter via `$FLOWCTL cat <task-id>`. Codex mirror regenerated.

baseline: green (test_command_shim_flatten pre-edit, rc=0)

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)
## Evidence
- Commits: 81b713838462e844e75e19476c264d09db136190
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_visual_skill test_command_shim_flatten -q (21 tests, OK), python3 scripts/run_tests_parallel.py (192 files, 4505 tests, 0 failures), uvx ruff@0.16.0 check . (All checks passed), ./scripts/sync-codex.sh x2 (rc=0 both, idempotent)
- PRs:
stage: plan-sync - skipped(empty: no downstream todo tasks)
