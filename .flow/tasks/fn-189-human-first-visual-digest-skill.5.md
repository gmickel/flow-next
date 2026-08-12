---
satisfies: [R8, R9]
---
# fn-189-human-first-visual-digest-skill.5 Conduct checklist + prose-contract tests + dogfood

## Description
(1) `agent_docs/conduct/visual.md`: 4-6 falsifiable transcript-checkable behaviors (digest fits one screen; every file-tree path exists in a task file, spec, or diff; no mermaid when a text shape sufficed; a prose sentence precedes every visual; coverage line matches `show --json` satisfies arrays; read-only - no writes). Index row in `agent_docs/conduct/README.md`. Never referenced from the skill's own files. (2) New `plugins/flow-next/tests/test_visual_skill.py` per the prose-contract heuristic (pin CONTENT + REACHABILITY, location only where load-bearing): shim bare name `name: visual`; description NL trigger phrases; all 8 vocabulary shapes present in the skill dir; the three closer offer lines (content in each skill + the line names /flow-next:visual); the make-pr sketch clause in its home file. (3) Dogfood once: run the skill against THIS spec post-plan in a real session; walk the conduct checklist, mark each item pass/fail in the task summary; fix prose that fails. (4) Final gate: focused suites + `./scripts/sync-codex.sh` twice + `uvx ruff@0.16.0 check .` (no flowctl.py changes expected, so no dual-copy/manifest steps - verify with git status).

## Acceptance
R8: conduct file + index row, transcript-checkable items only. R9: test file green, pins per heuristic. Dogfood transcript walked against conduct list with per-item pass/fail recorded in the task summary.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
