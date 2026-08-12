---
satisfies: [R1]
---
# fn-188-land-opt-in-repo-merge-verdict-command.1 Config plumbing: land.mergeVerdictCommand leaf + schema + docs row + config tests

## Description
R1 - Add land.mergeVerdictCommand (default "") to get_default_config()'s land block in plugins/flow-next/scripts/flowctl.py (~:1363; note the header comment style of the existing seven leaves; state in the comment that unset, null, and "" all mean OFF - contrast with cleanReviewCommentPattern where null and "" differ). Extend scripts/gen_flow_config_schema.py: DESCRIPTIONS entry in the land block (~:341-376) + the value shape in the TABLE (~:728-735 region; land is an object container - add the leaf like its siblings), regenerate the committed artifact plugins/flow-next/schema/flow-config.schema.json by RUNNING the script. Add a config row to plugins/flow-next/docs/flowctl.md next to the other land.* rows (~:981-987). Tests in plugins/flow-next/tests/test_land_config.py, matching its existing style: fresh-repo default is "", config set round-trip, sibling-no-clobber. Keep test_flow_config_schema_drift green (a defaults leaf + TABLE row is all a skill-read key needs - no ALLOWLIST entry). Do NOT touch the land skill prose (task 2 owns it) and do NOT add any new flowctl subcommand or logic.

## Acceptance
R1 met; cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_config_schema_drift -q green; schema artifact regenerated and committed; ruff clean.

## Done summary
land.mergeVerdictCommand config leaf (default "", unset/null/"" all OFF with the cleanReviewCommentPattern-contrast comment), schema generator DESCRIPTIONS + TABLE (string|null), regenerated committed schema artifact, docs/flowctl.md config row, 7 config tests. test_land_config + test_flow_config_schema_drift green (67 tests), ruff clean.
## Evidence
- Commits: aa1bc203
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_config_schema_drift -q
- PRs: